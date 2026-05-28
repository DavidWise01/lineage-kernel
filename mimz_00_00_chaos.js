// mimz_00_00_chaos.js — Dynamic Nested Memory
export const Chaos = {
  memory: new Uint8Array(8).fill(0),
  cycle: 0,
  
  // x+ output
  x_plus(vector) {
    const out = vector.map(v => v < 0 ? 255 + v : v);
    for(let i=0; i<4; i++) this.memory[i] = (this.memory[i] + out[i]) & 0xFF;
    return out;
  },
  
  // x- input  
  x_minus(vector) {
    const inp = vector.map(v => v > 0 ? v : 0);
    for(let i=4; i<8; i++) this.memory[i] = (this.memory[i] + inp[i-4]) & 0xFF;
    return inp;
  },
  
  // feedback loop
  tick() {
    this.cycle++;
    // x+ writes
    this.x_plus([-1,-1,0,0]);
    // memory evolves (chaos)
    for(let i=0; i<8; i++) {
      this.memory[i] = (this.memory[i] * 1103515245 + 12345) & 0xFF;
    }
    // x- reads
    this.x_minus([1,1,0,0]);
    
    return {
      memory: Array.from(this.memory).map(b=>b.toString(16).padStart(2,'0')).join(''),
      cycle: this.cycle,
      chaos: this.memory.reduce((a,b)=>a+b,0) / 2040
    };
  },
  
  // inject document
  nest(docHash) {
    const bytes = Uint8Array.from(docHash.match(/.{2}/g).map(h=>parseInt(h,16)));
    for(let i=0; i<8; i++) this.memory[i] ^= bytes[i % bytes.length];
  }
};

// Auto-run
if(typeof window !== 'undefined') {
  window.Chaos = Chaos;
  setInterval(() => Chaos.tick(), 16);
}
