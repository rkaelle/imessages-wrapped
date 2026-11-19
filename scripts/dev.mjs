import { spawn } from 'node:child_process';
const children = [spawn('venv/bin/python', ['-B','-m','backend.server'],{stdio:'inherit'}),spawn('npm',['--prefix','frontend','run','dev'],{stdio:'inherit'})];
for (const signal of ['SIGINT','SIGTERM']) process.on(signal,()=>{children.forEach(c=>c.kill(signal));process.exit()});
for (const child of children) child.on('exit', code=>{children.forEach(c=>c.kill());process.exit(code??0)});
