<?php
namespace App;

use Symfony\Bundle\FrameworkBundle\FrameworkBundle;
use Symfony\Bundle\FrameworkBundle\Kernel\MicroKernelTrait;
use Symfony\Bundle\TwigBundle\TwigBundle;
use Symfony\Component\DependencyInjection\Loader\Configurator\ContainerConfigurator;
use Symfony\Component\HttpKernel\Kernel as BaseKernel;
use Symfony\Component\Routing\Loader\Configurator\RoutingConfigurator;
use Symfony\UX\StimulusBundle\StimulusBundle;

final class Kernel extends BaseKernel
{
    use MicroKernelTrait;

    public function registerBundles(): iterable
    {
        yield new FrameworkBundle();
        yield new TwigBundle();
        yield new StimulusBundle();
    }

    public function getProjectDir(): string
    {
        return dirname(__DIR__);
    }

    protected function configureContainer(ContainerConfigurator $container): void
    {
        $container->extension('framework', [
            'test' => $this->environment === 'test',
            'router' => ['utf8' => true],
            'asset_mapper' => [
                'paths' => [
                    '%kernel.project_dir%/assets' => '',
                    '%kernel.project_dir%/node_modules/@hotwired/stimulus/dist' => '@hotwired/stimulus',
                ],
                'importmap_polyfill' => false,
            ],
        ]);
        $container->extension('twig', [
            'default_path' => '%kernel.project_dir%/templates',
            'strict_variables' => true,
            'cache' => false,
        ]);
        $services = $container->services()->defaults()->autowire()->autoconfigure();
        $services->set(TitleRule::class);
        $services->set(ReadingController::class)->public()->tag('controller.service_arguments');
    }

    protected function configureRoutes(RoutingConfigurator $routes): void
    {
        $routes->add('reading', '/')->controller(ReadingController::class)->methods(['GET', 'POST']);
    }
}
