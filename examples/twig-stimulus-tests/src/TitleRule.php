<?php
namespace App;

final class TitleRule
{
    public function accept(string $input): ?string
    {
        $title = trim($input);
        $length = mb_strlen($title, 'UTF-8');
        return $length >= 3 && $length <= 40 ? $title : null;
    }
}
