set owned_video_verified 0
set source_status_read_retries 0
if {[catch {
connect -url tcp:127.0.0.1:3121
jtag targets -set 1
puts "PREVIOUS_JTAG_CLOCK [jtag frequency]"
if {[jtag frequency 1000000] != 1000000} {error "Could not select 1MHz JTAG clock"}
puts "VIDEO_JTAG_CLOCK [jtag frequency]"
targets -set -filter {name == "APU"}
loadhw -hw {D:/Vivado/TileLab_RealPhotos_20261020/v179_hw01/system.xsa}
if {[expr [lindex [mrd -value 0x05f00008 1] 0]] != 3579349851} {error "Boot identity changed"}
proc halt_core {} {if {[catch {stop} why] && $why ne "Already stopped"} {error $why}}
targets -set -filter {name =~ "ARM*#0"}
halt_core
targets -set -filter {name =~ "ARM*#1"}
halt_core
proc halt_proof {marker} {puts "HALT_${marker}_BEGIN";puts [targets];puts "HALT_${marker}_END"}
halt_proof START
targets -set -filter {name == "APU"}
if {[expr [lindex [mrd -value 0x43c20000 1] 0]] != 1} {error "PL video is not enabled"}
if {[expr [lindex [mrd -value 0x43c20030 1] 0]] != 391118849} {error "Video version changed"}
set owned_video_verified 1
set version 391118849
if {($version == 0x17200001 || $version == 0x17500001)} {
 set color_before [mrd -value 0x43c20038 4]
 if {[expr [lindex $color_before 0]] != 260} {error "Color profile mismatch"}
if {[expr [lindex $color_before 1]] != 314} {error "Color profile mismatch"}
if {[expr [lindex $color_before 2]] != 403} {error "Color profile mismatch"}
if {[expr [lindex $color_before 3]] != 1} {error "Color profile mismatch"}
}
set items {4a353fd8d1a2c8a7324ee1e3 5056506dfdba312db8be7c685430515a226280708e5ac346fde2397759d7caf0 6c2232b3e0e796e9cd15c876 4d1334d95a70d6984386d2124b539eb7e4a61d9b8badd327ffcb3d116bce93b6 d7db13080292f0104c87580f e8f78a08404ce3e97695b9357c34eb8664345248b8354e25ee51933edeedc286 ba4a38dbb8da945992a3bfa0 e97e142383ba118966d4582129d0ecbc18403d6507c1027e1b2d64523582f3f5 d257193bbbe1a6a4429fcc37 ca218fc3ad03a1915faf5b98fdfdcfdda144881bfeb44b68434274812578b500 eba4fda0df189ce000b7b5a8 0454b77297a360b7cc235365df40e63f9607fd02728395d71556c2ac1540d86b 3f4485b26dd123f31c041d62 6db54082950d72f4332b86f9a05cfa430f35b6b3d95ef291db105edbb3552776 fba9dc4e6de6e9798bfbd766 5072074b264726d04dd86d847ec7109391442a10c87811e077e2bf481ce757d4 3d7b2dff36e73a50a8d772c1 d81179c0b9b0241f3b751f71e29a8ee5b4f60b34e30aec2dcee42cbbc7f0bd12 ce645bc6719954fb261d992c a89251e5c879f9fbe900d2853c07ed05f41b31bafe85bddbe9b05f88b1d909bb ec28e41000ab845c962d09a2 75f4bbdd22c5b06aca65a3ac68e181191a28454223f6ebe1517fe8b568058b65 5cfe08cd40d54dc81a31ff95 86f1f6cdfc82ba8f97b70740c24114862567c76c378bcab1032ffbf4537cfddc 45d16dc97d866af254455ed5 2d9378af019fdfc7a5c64aabd8662945e029c3214150b5d9511405a054588750 c87db716fd5f01f06a2366ce 5d19dcdcc546306b17de01fe55afa2916c4b98b4a2684e9ce70a6c0c18b3f3a1 b510dd85123ede9d95bfd690 4c6af8a9281c926257b66f561ef5ccd848131fcc82c05ef7d3ca4af2e0b1447a a08eb0c2185fe914f39bf224 38cf1ba681c924334952ff1cdb92610f9b181029757537927528cf8cb568e993 0b5b3299e030bf7788c2fad1 ac5bee94e1de3f74ce3d517c75d801d12c8ab105104445da415d41330e12ce62 7d5203eb7ab440f678e9d7c1 4856f87c9a5596fcb9572aece199262aa31327415b78a1e58a804dfac2b4e9bf effd71fb9a949bf0ac76adb1 95aec677bf382a9ea8981cbc3832de9c3c64298eebdd71df9d6e6b35467eb989 ba83f807620c4b4e68af6d24 1e7f5fe235c59a12b0adfab4450ff452a9c80862850d766a52a83f87c3dc9cb9 9df4c2962faf785116eb2f74 fa43fe3f80bbb291021ffea87d5d55bcba418ca3f8b9d6f5a16da9b644edd8ee 9e066f00fc437d3bf641a0c8 c0ee0c064ef2d91f6907261d64ffe5b39d99c7c270725a914c2d125e4e023a09 cb3c0d7c6824c24fa01ed5d0 023162f13076deb34db6030ad82e64c9107bc0b445cfd2780cb40dae834ee4aa f03f95cab74648ae16024457 3addbb87bd5fcde10dccfa1d5f131ddcb6c4a793feb2ebf6aceb23d49c0b4a6f 9cc4a74948f607f8f53c271e 58890fe4799a5692567fec099246e9571bb0e15f44d0305239d0dd70e9939c0c 150af80bb7fdab15bb7ba694 a9e88d7585f93756970f162f5d52e310fb153c243c13b3544e2a3a5e69ec5587 a22c50704234bb5dd86c48be d399c6e7880d0c15e34778dfe98b6cb3a2a3f8a90b71ad4076c5bc54b95fe451 8e3b3803bee9ee853faed5d0 608a3030d22fcc1a4ccc2bf332321836ed0f16b1dfe59c9d77c20f87266d6aa0 f2d3410326542c31b90c48f2 8477c520b1a252843a4515b52ccd7382c3abb3e88101dd2da8828c2b97cccb36 a44964923918b89befa2d12b 6692987f6efba023c2764ab5cd03859809f55922f973eec85a937ab6adf19e2d e71c229f5175be77b32cf42d bfb9d781a89846ed519527f1f964ed2117bedfbb968aefed68cd8ca3657d748f 37b8842b3828c90b87007b60 940020bbfa328e4f76e418336cf908c0d47469f263f9fa48e578ac9f69b603cb e9839975060cd30a58458c71 55a0aa6797c969fe303ff4d738f2eef90e03a69738b2ac3c7a320703e2e21c13 3fa963c02c25b32a1a5b4d5d d542b9572c5d877adaee466c0b1844ea3445bae3e12ece6b39ff596cc3b33cb5 a406cd850ed52db0e0b40a42 565545b053c5655a2e63c8dd560a1c50dd36ae2db3d79273bce24ecd6f3d313f 2bd8b1c1804cc762bf1aafd2 8e0ee2068651cd3720407a5a99d4acaa78ae5c9d67978e2a0e42f69e2ae989de 36f140848b709c49580e50f0 ab194c7683f9807609ccf8f6753d98762032b7db1c0d1daed39c238b81476099 93e5ed4eb9d33d1fc5cac0a2 494b7cb5d65627ed431e7a2366adda7c6f5bd85963876c78173c345467b635bd 013c64582edbb0b3c7b8cebb 1aca5ad738caec702c051e93170330957c85c14f70b66c2402ba891c82f23bb2 04c3a7dc9009b68b4b43963d e8aca9fc9503fa963d3b541d760570919fcf99531f2b608ec1cdb4b4c881e983}
set source_status {D:/Vivado/TileLab_RealPhotos_20261020/v194_hdmi01/source/status.json}
set source_command {D:/Vivado/TileLab_RealPhotos_20261020/v194_hdmi01/source/command.txt}
set output {D:/Vivado/TileLab_RealPhotos_20261020/v194_hdmi01/external40}
proc current_source {id hash} {
 global source_status source_status_read_retries
 set readable 0
 for {set attempt 0} {$attempt<100} {incr attempt} {
  set f ""
  set failed [catch {set f [open $source_status r];set data [read $f]} why]
  if {$f ne ""} {catch {close $f}}
  if {!$failed} {set readable 1;break}
  incr source_status_read_retries
  puts "SOURCE_STATUS_READ_RETRY $id $attempt $why"
  after 30
 }
 if {!$readable} {error "Source status unavailable"}
 foreach token [list "\"image_id\":\"$id\"" "\"original_sha256\":\"$hash\"" {"physical_window_bounds_verified":true} {"running":true} {"paused":true} {"calibration_pattern":false}] {
  if {[string first $token $data]<0} {return ""}
 }
 return $data
}
foreach {id hash} $items {
 set f [open $source_command w];puts $f "photo:$id";close $f
 set source ""
 for {set i 0} {$i<40} {incr i} {
  after 100
  if {![catch {set source [current_source $id $hash]}] && $source ne ""} {break}
 }
 if {$source eq ""} {error "Source player did not acknowledge original $id"}
 after 650
 set before [mrd -value 0x43c20000 14]
 set base [expr [lindex $before 2]]
 set fresh 0
 for {set i 0} {$i<40} {incr i} {
  after 100
  set values [mrd -value 0x43c20000 14]
  if {[expr [lindex $values 6]]} {error "PL fault during $id"}
  if {(([expr [lindex $values 2]]-$base)&0xffffffff)>=3} {set fresh 1;break}
 }
 if {!$fresh} {error "No three fresh detections for $id"}
 for {set sample 0} {$sample<3} {incr sample} {
  if {[current_source $id $hash] eq ""} {error "Input changed during $id"}
  set values [mrd -value 0x43c20000 14]
  puts "PHOTO_RESULT $id [clock milliseconds] $values"
  after 250
 }
 set source [current_source $id $hash]
 if {$source eq ""} {error "Input changed after $id"}
 set f [open "$output/${id}_source.json" w];puts $f $source;close $f
 halt_proof $id
}
mwr 0x43c20000 0
set drained 0
for {set i 0} {$i<100} {incr i} {
 if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set drained 1;break}
 after 100
}
if {!$drained} {error "Final input buffer did not drain"}
if {($version == 0x17200001 || $version == 0x17500001) && [mrd -value 0x43c20038 4] ne $color_before} {error "Color profile changed"}
halt_proof FINAL
puts "SOURCE_STATUS_READ_RETRIES $source_status_read_retries"
puts "HDMI_PHOTO_SERIES_COMPLETE"
disconnect
} why opts]} {
 puts stderr $why
 if {[dict exists $opts -errorinfo]} {puts stderr [dict get $opts -errorinfo]}
 if {$owned_video_verified} {
  catch {
   targets -set -filter {name == "APU"}
   mwr 0x43c20000 0
   set drained 0
   for {set i 0} {$i<100} {incr i} {
    if {!([expr [lindex [mrd -value 0x43c20004 1] 0]] & 1)} {set drained 1;break}
    after 100
   }
   puts "FAILED_EXPERIMENT_VIDEO_DISABLED_DRAINED $drained"
  }
 }
 catch {disconnect}
 exit 1
}
exit 0
