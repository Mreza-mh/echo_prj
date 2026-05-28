<?php

namespace App\Enums;

enum UserRole:string
{
    case admin = 'admin';
    case user = 'user';
    case doctor = 'doctor';
    case nurse = 'nurse';
    case operator = 'operator';
    case monshi = 'monshi';



    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
