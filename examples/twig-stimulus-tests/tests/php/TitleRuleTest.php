<?php
namespace App\Tests;

use App\TitleRule;
use PHPUnit\Framework\TestCase;

final class TitleRuleTest extends TestCase
{
    public function testServerTrimsAndAcceptsOrdinaryTitles(): void
    {
        self::assertSame('Read a chapter', (new TitleRule())->accept('  Read a chapter  '));
        self::assertSame('猫の本', (new TitleRule())->accept('猫の本'));
        self::assertSame(str_repeat('a', 40), (new TitleRule())->accept(str_repeat('a', 40)));
    }

    public function testServerRejectsShortOrLongTitles(): void
    {
        foreach (['', '  ', 'ab', str_repeat('a', 41)] as $title) {
            self::assertNull((new TitleRule())->accept($title));
        }
    }
}
