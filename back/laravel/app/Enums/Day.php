<?php

namespace App\Enums;

enum Day: string
{
    case saturday = 'saturday';
    case sunday = 'sunday';
    case monday = 'monday';
    case tuesday = 'tuesday';
    case wednesday = 'wednesday';
    case thursday = 'thursday';
    case friday = 'friday';

    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }

}
