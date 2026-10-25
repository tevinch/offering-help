<?php
require dirname(__DIR__).'/vendor/autoload.php';

use App\Kernel;
use Twig\Environment;

$run = $argv[1] ?? '';
if ($run === '') {
    throw new InvalidArgumentException('Supply the current fixture run identifier.');
}
$kernel = new Kernel('test', true);
try {
    $kernel->boot();
    $twig = $kernel->getContainer()->get('test.service_container')->get(Environment::class);
    $html = $twig->render('_title_form.html.twig', ['title' => '']);
    $directory = dirname(__DIR__).'/var/fixtures';
    if (!is_dir($directory) && !mkdir($directory, 0777, true) && !is_dir($directory)) {
        throw new RuntimeException('Cannot create fixture directory.');
    }
    $bytes = file_put_contents($directory.'/title-form.json', json_encode([
        'run' => $run,
        'html' => $html,
    ], JSON_THROW_ON_ERROR | JSON_PRETTY_PRINT));
    if ($bytes === false) {
        throw new RuntimeException('Cannot write rendered fixture.');
    }
    echo "Rendered the shared Twig form.\n";
} finally {
    $kernel->shutdown();
}
