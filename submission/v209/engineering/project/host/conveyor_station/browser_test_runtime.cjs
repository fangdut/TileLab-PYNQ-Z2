// SPDX-License-Identifier: MIT
// Install with: npm install --no-save playwright
const path=require('path'),fs=require('fs');
exports.browser=()=>require(process.env.TILELAB_PLAYWRIGHT_MODULE||'playwright');
exports.encoder=()=>{
 if(process.env.TILELAB_FFMPEG)return process.env.TILELAB_FFMPEG;
 const vendor=path.join(__dirname,'tools_vendor','imageio_ffmpeg','binaries');
 if(fs.existsSync(vendor)){const f=fs.readdirSync(vendor).find(n=>n.endsWith('.exe')||n.startsWith('ffmpeg-'));if(f)return path.join(vendor,f)}
 return 'ffmpeg';
};
