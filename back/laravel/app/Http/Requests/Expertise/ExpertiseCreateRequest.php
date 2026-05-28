<?php

namespace App\Http\Requests\Expertise;

use Illuminate\Foundation\Http\FormRequest;

class ExpertiseCreateRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'title' => ['required', 'string', 'max:255'],
            'label' => ['required', 'string', 'max:255'],
        ];
    }

    public function messages(): array
    {
        return [
            'title.required' => 'عنوان الزامی است.',
            'title.string'   => 'عنوان باید متن باشد.',
            'title.max'      => 'عنوان نباید بیش از ۲۵۵ کاراکتر باشد.',

            'label.required' => 'عنوان فارسی الزامی است.',
            'label.string'   => 'عنوان فارسی باید متن باشد.',
            'label.max'      => 'عنوان فارسی نباید بیش از ۲۵۵ کاراکتر باشد.',
        ];
    }
}
