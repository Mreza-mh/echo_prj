<?php

namespace App\Enums;

enum LoginMethod:string
{
    case password = 'password';
    case sms = 'sms';
    case both = 'both';
}
