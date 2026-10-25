# Testing Twig and Stimulus together

This small Symfony application checks a reading-list title. PHP owns the rule (a trimmed title must contain 3–40 Unicode code points); Stimulus shows a live character count. Submitting the ordinary form always asks PHP for the final result. Nothing is stored and no external service is called.

## Run it

Use PHP 8.4.1+ with `dom`, `filter`, `mbstring`, `openssl`, `phar`, `tokenizer`, `xml` and `xmlwriter`, Composer 2, and Node 24.15+ (24.x).

```sh
composer install --no-interaction
npm ci
npx playwright install chromium
php vendor/bin/phpunit
npm run test:dom
npm run test:browser
```

`npm run test:browser` starts and stops its own PHP server on `127.0.0.1:8765`; keep that port free. Its Chromium instance uses a disposable test profile. To browse the example separately:

```sh
php -S 127.0.0.1:8000 -t public public/index.php
```

Open <http://127.0.0.1:8000/>. Submit `ab` to see the server's rejection, then `Read a chapter` to see its accepted title. JavaScript adds immediate counting; the form still works without it. The example uses development asset serving; a deployment needs the normal AssetMapper production build.

## 1. Where should the logic live?

Keep rules that decide an accepted operation on the server. Fast presentation changes can stay in the controller: counting characters, revealing fields or formatting a preview need no request. A client can also preview a server rule, but PHP must still enforce it when the operation is submitted.

Here `src/TitleRule.php` owns acceptance and normalization. The controller counts the raw input only; it does not implement the title-validity rule. The count can therefore include surrounding spaces which PHP later trims. This makes each test layer responsible for different evidence.

## 2. Which tests belong where?

| Layer | This example verifies | What it does not repeat |
| --- | --- | --- |
| PHPUnit unit | Trimmed boundaries and Unicode cases in the authoritative title rule | Stimulus actions or DOM state |
| PHPUnit application | A real Symfony kernel handles GET, invalid POST and subsequent valid POST; returned HTML shows the server result | JavaScript execution |
| Stimulus + DOM | The actual controller connects to real Twig markup; targets/actions update the count; removal unbinds actions; reinsertion reconnects; another document starts cleanly | PHP rule permutations or browser layout |
| Browser | The real route loads mapped controller assets, input updates feedback, and repeated submissions show real HTTP responses | Every boundary already covered in PHP |

A simple controller does not need an extra pure-JavaScript unit suite just to fill a test category. If meaningful client-only calculations grow, extract them and test those separately. DOM tests do not cover layout, browser focus behavior or every browser API; use the browser for behavior that depends on those.

## 3. Actual Twig or hand-written HTML?

Small hand-written DOM fragments are useful for isolated controller variants. Keep at least one integration path against the actual template contract. This example renders `templates/_title_form.html.twig` both in the application page and in `bin/render-fixture.php`. There is no second maintained copy of its data attributes.

The production route loads `assets/app.js` through Symfony AssetMapper and the StimulusBundle loader. The DOM test imports the same controller class and registers it with a real Stimulus `Application`. It waits for registration on the element independently of any callback assertions. Stimulus, rather than a direct method call, handles input actions and the connection lifecycle.

## 4. How does the fixture stay current?

`npm run test:dom` calls `bin/test-dom.mjs`, which boots the Symfony test kernel through the PHP generator, renders the shared Twig partial with strict variables, and only then starts the DOM tests. A generator failure stops the command. The generated JSON contains the rendered HTML and a per-run identifier; the test rejects a missing or earlier run's fixture.

Keep that complete command in CI:

```sh
composer install --no-interaction
npm ci
npx playwright install --with-deps chromium
php vendor/bin/phpunit
npm run test:dom
npm run test:browser
```

To check the contract, temporarily rename `data-title-count-target="count"` in the **Twig partial**, then run `npm run test:dom`: it must fail after regeneration. Restore it and rerun. Removing the `input->title-count#update` action must also fail. This checks the template used by the app, rather than a stale test-only HTML file.

## 5. Should generated fixtures be committed?

For a template and controller in the same repository, generate fixtures during the test command and ignore `var/`. That is this example's choice. Use synthetic content and pass no secrets or real user data to the renderer.

Committed snapshots can make sense when the rendered output is deliberately reviewed, or another repository consumes a stable fixture. In that arrangement, document the regeneration command and make CI regenerate and reject a diff. Committing HTML alone does not prevent drift.

## Files to adapt

Start with the shared Twig partial, `bin/render-fixture.php`, `bin/test-dom.mjs` and `tests/dom/title-count.test.mjs`. Replace the synthetic title operation with your application's real operation. Keep an application request test and one browser path that finishes the operation and inspects its visible server result.

Versions are pinned in `composer.lock` and `package-lock.json`. This consumer example demonstrates a tested workflow. Adapt the cases to your own controller behavior.

References: [Symfony testing](https://symfony.com/doc/current/testing.html), [AssetMapper](https://symfony.com/doc/current/frontend/asset_mapper.html), [StimulusBundle](https://symfony.com/bundles/StimulusBundle/current/index.html), [Stimulus lifecycle](https://stimulus.hotwired.dev/reference/lifecycle-callbacks).

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
