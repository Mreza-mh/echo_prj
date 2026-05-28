<?php

namespace App\Http\Requests\Service;

use App\Enums\UserRole;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
class ServiceFilterRequest extends FormRequest
{
    protected $stopOnFirstFailure = true;
    public function authorize()
    {
        return true;
    }
    protected function failedValidation(Validator $validator)
    {
        $errorMessage = $validator->errors()->first();
        throw new HttpResponseException(response()->json(['message' => $errorMessage,'success' => false], 400));
    }
    public function rules(): array
    {
        return [
            'is_paginate' => 'nullable|boolean',
            'count_item' => 'nullable|integer',
            'title'           => 'nullable|string|max:255',
        ];
    }

    public function messages(): array
    {
        return [
            'title.string'   => 'عنوان باید به صورت متن وارد شود.',
            'title.max'      => 'عنوان نباید بیش از ۲۵۵ کاراکتر باشد.',
        ];
    }
}
