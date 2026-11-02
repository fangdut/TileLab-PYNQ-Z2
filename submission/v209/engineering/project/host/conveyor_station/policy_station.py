# SPDX-License-Identifier: MIT
"""Explicit no-alarm automatic-pass policy. Never creates a human review."""
from closed_station import ClosedStation
from controller import utc
from calibration import digest


class PolicyStation(ClosedStation):
    def __init__(self, backend, catalog, store, resume=None):
        super().__init__(backend,catalog,store)
        self.counts['automatic_passed']=0
        if resume:
            if resume['phase'] not in ['READY','RELEASED','SEGREGATED','REMOVED','REVIEW_HOLD','GOOD_HOLD','DEFECT_HOLD','CONFLICT_HOLD']:
                raise ValueError('不能迁移正在检测或处置的工件')
            loop=resume['closed_loop']
            material=loop.get('active_material')
            run=loop.get('run')
            if material and run:
                self.material_id=material['id'];self.run_id=run['id'];self.selection_id=loop['selection_id']
                self._context(True)
            self.connection=backend.check()
            self.counts.update(resume['counts'])
            self.cycle=resume.get('cycle')
            self.phase=resume['phase'];self.stop_requested=resume.get('stop_requested',False)
            if self.cycle:
                self._cycle_context(True);self._artifacts()
                r=self.cycle.get('result')
                if r and (r['boot_identity']!=self.connection['boot_identity'] or r['model_sha256']!=self.connection['model_sha256']):
                    raise ValueError('迁移结果的启动或模型身份已变化')
            self._event('pc_policy_upgrade_resumed',previous_session=resume['session'],
                result_revalidated=True,board_reprogrammed=False)
            if resume.get('restart_reason'):
                self._event('recording_session_restarted',reason=resume['restart_reason'],
                    previous_pending_cycle=resume.get('previous_pending_cycle'),
                    previous_cycle_review_fabricated=False)

    def state(self):
        s=super().state()
        s['automatic_pass_policy']=dict(enabled=True,id='FPGA_NO_ALARM_AUTO_PASS_V207',
            scope='SIMULATED_CONVEYOR_OPERATOR_AUTHORIZED',human_review_required_for_alarm=True,
            independent_accuracy_certified=False)
        return s

    def action(self,body):
        if body.get('op')!='automatic_release':return super().action(body)
        with self.lock:
            self._require(body)
            if body.get('policy_id')!='FPGA_NO_ALARM_AUTO_PASS_V207':raise ValueError('自动通过策略未确认')
            if self.phase!='REVIEW_HOLD' or not self.cycle or self.cycle.get('purpose')!='inspection':raise ValueError('当前工件不允许自动通过')
            self._cycle_context(True);self._check_review_artifacts()
            r=self.cycle.get('result') or {}
            if body.get('result_id')!=r.get('id') or r.get('pl_image_alarm')!=0 or self.cycle.get('review'):
                raise ValueError('仅当前未报警且未人工处置的新结果可以自动通过')
            self.phase='CONFIRMING';self._touch()
            self._event('automatic_pass_requested',policy='FPGA_NO_ALARM_AUTO_PASS_V207',
                human_review_performed=False,result_id=r['id'])
            ident=self.cycle['id'];self._launch(lambda:self._automatic_confirm(ident))
            return self.state()

    def _automatic_confirm(self,ident):
        try:
            connection=self.backend.check()
            with self.lock:
                if self.phase!='CONFIRMING' or self.cycle['id']!=ident:raise ValueError('自动通过任务已过期')
                context=self._cycle_context(True);self._artifacts()
                r=self.cycle['result']
                if r['pl_image_alarm']!=0 or connection['boot_identity']!=context['boot_identity'] or connection['model_sha256']!=context['profile_sha256']:
                    raise ValueError('自动通过前判定或板端身份变化')
                self.cycle['automatic_decision']=dict(policy_id='FPGA_NO_ALARM_AUTO_PASS_V207',
                    result_id=r['id'],result_sha256=r['result_sha256'],context_sha256=digest(context),
                    decision='pass_no_alarm',human_review_performed=False,utc=utc())
                self.cycle['disposition']=dict(command='automatic_pass',confirmed_by='系统自动策略（非人工复核）',
                    confirmed_utc=utc(),result_id=r['id'],review_id=None,physical_actuation_verified=False)
                self.connection=connection;self.phase='RELEASED';self.stop_requested=False
                self.counts['automatic_passed']+=1;self.counts['released']+=1
                self._touch();self._event('automatic_pass_confirmed',human_review_performed=False,result_id=r['id'])
                self._save_cycle(self.store/'cycles'/ident)
        except Exception as error:
            with self.lock:self._fault(error);self._save_cycle(self.store/'cycles'/ident)
