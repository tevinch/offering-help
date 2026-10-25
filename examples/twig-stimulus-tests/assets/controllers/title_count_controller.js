import { Controller } from '@hotwired/stimulus';

export default class extends Controller {
  static targets = ['title', 'count'];

  connect() {
    this.update();
  }

  update() {
    this.countTarget.textContent = `${Array.from(this.titleTarget.value).length} characters`;
  }
}
