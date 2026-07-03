<?php

namespace App\Http\Requests\Auth;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;

class FilterUserRequest extends FormRequest
{
    protected $stopOnFirstFailure = true;

    /**
     * Determine if the user is authorized to make this request.
     */
    public function authorize(): bool
    {
        return true;
    }

    protected function failedValidation(Validator $validator)
    {
        $errorMessage = $validator->errors()->first();
        throw new HttpResponseException(response()->json(['message' => $errorMessage], 400));
    }

    /**
     * Get the validation rules that apply to the request.
     */
    public function rules(): array
    {
        return [
            'count_item' => 'nullable|integer',
            'is_paginate' => 'nullable|boolean',
            'name'   => 'nullable|string',
            'mobile' => 'nullable|string',
            'id'     => 'nullable|integer|min:1',
        ];
    }
}
