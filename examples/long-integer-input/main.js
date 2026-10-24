import { createApp } from 'vue/dist/vue.esm-bundler.js';
import { vMaska } from 'maska/vue';
import { integerOptions } from './integer-options.js';

createApp({
  directives:{maska:vMaska},
  data:()=>({options:integerOptions,masked:'',raw:'',hooks:0,pastes:0,receipt:'',status:''}),
  methods:{
    onMask(event) { this.hooks++; event.target.setCustomValidity(''); },
    reject(event,text) {
      if(text && /[^0-9,]/.test(text)) {
        event.preventDefault();
        event.target.setCustomValidity('Use unsigned integer digits and optional grouping commas only.');
        this.status='Signs, decimal points and other characters are not supported.';
      }
    },
    onBeforeInput(event) { this.reject(event,event.data); },
    onPaste(event) { this.pastes++; this.reject(event,event.clipboardData.getData('text')); },
    async submit() {
      this.status='Submitting…'; this.receipt='';
      try {
        const response=await fetch('/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:this.raw})});
        const result=await response.json();
        if(!response.ok)throw Error(result.error);
        this.receipt=result.value; this.status='The local server received the exact digit string.';
      } catch(error) { this.status=error.message; }
    },
  },
  template:`
    <h1>Keep long integer digits exact</h1>
    <p>Type or paste <code>12345678901234567890</code>. Grouping commas are displayed while the raw value stays a string.</p>
    <p class="notice">This example accepts ASCII unsigned integer digits and optional commas. Signs, decimals, currency and locale-aware number formatting are outside its scope.</p>
    <form @submit.prevent="submit">
      <label for="digits">Integer digits</label>
      <input id="digits" type="text" inputmode="numeric" required v-model="masked" v-maska:raw.unmasked="options" @maska="onMask" @beforeinput="onBeforeInput" @paste="onPaste">
      <button type="submit">Submit string</button>
    </form>
    <p role="status">{{status}}</p>
    <dl><dt>Displayed string</dt><dd><output id="masked">{{masked}}</output></dd>
    <dt>Raw string</dt><dd><output id="raw">{{raw}}</output></dd>
    <dt>Server received</dt><dd><output id="receipt">{{receipt}}</output></dd></dl>
    <details><summary>Input events</summary><p>Mask callbacks: <output id="hooks">{{hooks}}</output>; paste events: <output id="pastes">{{pastes}}</output></p></details>
  `,
}).mount('#app');
