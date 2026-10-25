<?php
namespace App\Tests;

use Symfony\Bundle\FrameworkBundle\Test\WebTestCase;

final class ReadingPageTest extends WebTestCase
{
    public function testServerRespondsWithoutExecutingJavascript(): void
    {
        $client = self::createClient();
        $client->request('GET', '/');
        self::assertResponseIsSuccessful();
        self::assertSelectorExists('form[data-controller="title-count"]');
        $client->submitForm('Check title', ['title' => 'ab']);
        self::assertResponseStatusCodeSame(422);
        self::assertSelectorTextContains('#result', 'Use 3 to 40 characters.');
        $client->submitForm('Check title', ['title' => '  Read a chapter  ']);
        self::assertResponseStatusCodeSame(200);
        self::assertSelectorTextContains('#result', 'Accepted: Read a chapter');
        self::assertInputValueSame('title', 'Read a chapter');
    }
}
