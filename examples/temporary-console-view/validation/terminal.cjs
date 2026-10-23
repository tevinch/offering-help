const {Terminal} = require('@xterm/headless');
const readline = require('node:readline');
const terminal = new Terminal({cols: Number(process.argv[2]), rows: Number(process.argv[3]), allowProposedApi: true});
let replies = '';
terminal.onData(value => { replies += value; });
function lines(buffer) {
  return Array.from({length: buffer.length}, (_, i) => buffer.getLine(i).translateToString(true));
}
readline.createInterface({input: process.stdin}).on('line', line => {
  const message = JSON.parse(line);
  terminal.write(message.text || '', () => {
    const result = {type: terminal.buffer.active.type, active: lines(terminal.buffer.active), normal: lines(terminal.buffer.normal), replies};
    replies = '';
    process.stdout.write(JSON.stringify(result) + '\n');
  });
});
