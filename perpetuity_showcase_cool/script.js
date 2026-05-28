const canvas = document.getElementById('starfield');
const ctx = canvas.getContext('2d');
let w, h, dpr, particles;
function resize(){
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  w = canvas.width = innerWidth * dpr;
  h = canvas.height = innerHeight * dpr;
  canvas.style.width = innerWidth + 'px';
  canvas.style.height = innerHeight + 'px';
  particles = Array.from({length: Math.min(160, Math.floor(innerWidth/8))}, () => ({
    x: Math.random()*w, y: Math.random()*h, z: Math.random()*1 + .2, r: Math.random()*1.7 + .3
  }));
}
function draw(){
  ctx.clearRect(0,0,w,h);
  ctx.fillStyle = 'rgba(255,0,77,.55)';
  for(const p of particles){
    p.y += p.z * .28 * dpr;
    p.x += Math.sin((p.y+p.x)*.0009) * .14 * dpr;
    if(p.y > h){p.y = -10; p.x = Math.random()*w;}
    ctx.globalAlpha = .18 + p.z*.35;
    ctx.beginPath(); ctx.arc(p.x,p.y,p.r*dpr,0,Math.PI*2); ctx.fill();
  }
  ctx.globalAlpha = 1;
  requestAnimationFrame(draw);
}
addEventListener('resize', resize, {passive:true});
resize(); draw();
