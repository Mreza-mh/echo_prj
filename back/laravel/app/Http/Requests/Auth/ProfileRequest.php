<?php

namespace App\Http\Requests\Auth;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
class ProfileRequest  extends FormRequest
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
            'name'     => 'string|min:2|max:100',
            'birthday' => [
                'nullable',
                'regex:/^\d{4}\/\d{1,2}\/\d{1,2}$/', // فرمت 1402/05/19
            ],
        ];
    }

    public function messages(): array
    {
        return [
            'name.min'      => 'طول نام باید حداقل ۲ کاراکتر باشد.',
            'birthday.regex' => 'تاریخ تولد باید در قالب صحیح (مثلاً 1402/05/19) وارد شود.',
            ];
    }
}
