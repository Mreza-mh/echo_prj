<?php

namespace App\Enums;

//use App\Enums\Setting\Authentication;

enum KeySetting:string
{

    case SendSmsAfterInvite = 'SendSmsAfterInvite';

    // public static function getValidValues(self $key):array {

    //     return match ($key) {
    //         self::AuthenticationType => array_map(fn($key) => $key->value, Authentication::cases()),
    //         self::NumberOfDigitsSms => range(4, 8),
    //     };

    // }

    public static function values(): array
    {
        return array_column(self::cases(), 'value');
    }
}
