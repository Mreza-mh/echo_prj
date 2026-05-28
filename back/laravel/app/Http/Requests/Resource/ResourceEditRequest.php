<?php

namespace App\Http\Requests\Resource;

use Illuminate\Foundation\Http\FormRequest;
use App\Enums\ResourceType;

class ResourceEditRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'resource_name'   => ['nullable', 'string', 'max:255'],
            'resource_type'   => ['nullable', 'in:' . implode(',', ResourceType::values())],
        ];
    }

    public function messages(): array
    {
        return [
            'resource_name.string'   => 'نام منبع باید متن باشد.',
            'resource_name.max'      => 'نام منبع نباید بیش از ۲۵۵ کاراکتر باشد.',

            'resource_type.in'       => 'نوع منبع معتبر نیست.',
        ];
    }
}
