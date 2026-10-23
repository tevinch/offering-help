import { prepareCopy } from './operation.js';
const fileInput = document.querySelector('#file');
const form = document.querySelector('#form');
const button = document.querySelector('#remove');
const status = document.querySelector('#status');
const download = document.querySelector('#download');
let outputUrl;
let busy = false;
function clearDownload() {
  download.hidden = true;
  download.removeAttribute('href');
  if (outputUrl) URL.revokeObjectURL(outputUrl);
  outputUrl = undefined;
}
fileInput.addEventListener('change', () => {
  clearDownload();
  button.disabled = !fileInput.files.length || busy;
  status.textContent = fileInput.files.length ? 'Ready to prepare a separate copy.' : 'Choose a JPEG.';
});
button.addEventListener('click', async () => {
  const file = fileInput.files[0];
  if (!file || busy) return;
  busy = true;
  button.disabled = fileInput.disabled = form.disabled = true;
  clearDownload();
  status.textContent = 'Preparing copy… The first run loads the image tools.';
  try {
    const data = await prepareCopy(file, form.value);
    outputUrl = URL.createObjectURL(new Blob([data], { type: 'image/jpeg' }));
    download.href = outputUrl;
    download.download = file.name.replace(/\.(jpe?g)$/i, '') + '-without-trailer.jpg';
    download.hidden = false;
    status.textContent = 'Copy ready. Save it using the link below; your selected file is unchanged.';
  } catch (error) {
    status.textContent = 'Could not prepare copy: ' + error.message;
  } finally {
    busy = false;
    fileInput.disabled = form.disabled = false;
    button.disabled = !fileInput.files.length;
  }
});
window.addEventListener('pagehide', clearDownload);
