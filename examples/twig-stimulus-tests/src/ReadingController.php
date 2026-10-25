<?php
namespace App;

use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Twig\Environment;

final class ReadingController
{
    public function __invoke(Request $request, Environment $twig, TitleRule $rule): Response
    {
        $title = '';
        $result = 'Enter a title to check.';
        $status = 200;
        if ($request->isMethod('POST')) {
            $title = $request->request->getString('title');
            $accepted = $rule->accept($title);
            if ($accepted === null) {
                $result = 'Use 3 to 40 characters.';
                $status = 422;
            } else {
                $title = $accepted;
                $result = 'Accepted: '.$title;
            }
        }
        return new Response($twig->render('reading.html.twig', [
            'title' => $title,
            'result' => $result,
        ]), $status);
    }
}
