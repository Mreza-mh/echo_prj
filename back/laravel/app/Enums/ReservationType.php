<?php

namespace App\Enums;

enum ReservationType: string
{
    case Online = 'Online';
    case Phone = 'Phone';
    case Walk_in = 'Walk_in';
    case Special = 'Special';

    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }

}
