<?php

namespace App\Http\Requests\Resource;

use Illuminate\Foundation\Http\FormRequest;
use App\Enums\ResourceType;

class ResourceCreateRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'resource_name'   => ['required', 'string', 'max:255'],
            'resource_type'   => ['required', 'in:' . implode(',', ResourceType::values())],
        ];
    }

    public function messages(): array
    {
        return [
            'resource_name.required' => 'نام منبع الزامی است.',
            'resource_name.string'   => 'نام منبع باید متن باشد.',
            'resource_name.max'      => 'نام منبع نباید بیش از ۲۵۵ کاراکتر باشد.',

            'resource_type.required' => 'نوع منبع الزامی است.',
            'resource_type.in'       => 'نوع منبع معتبر نیست.',
        ];
    }
}
