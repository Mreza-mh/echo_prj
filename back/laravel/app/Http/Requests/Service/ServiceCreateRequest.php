<?php

namespace App\Http\Requests\Service;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
class ServiceCreateRequest extends FormRequest
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
            'title'           => 'required|string|max:255',
            'duration'=> 'nullable|date_format:H:i:s',
            'price'   => 'nullable|numeric|min:0|digits_between:1,12',
        ];
    }

    public function messages(): array
    {
        return [
            'title.required' => 'عنوان الزامی است.',
            'title.string'   => 'عنوان باید به صورت متن وارد شود.',
            'title.max'      => 'عنوان نباید بیش از ۲۵۵ کاراکتر باشد.',

            'duration.date_format' => 'مدت‌زمان باید در قالب HH:MM:SS وارد شود.',

            'price.numeric'         => 'قیمت باید به صورت عددی وارد شود.',
            'price.digits_between'  => 'قیمت باید بین ۱ تا ۱۲ رقم باشد.',
            'price.min'             => 'قیمت نباید مقدار منفی داشته باشد.',
        ];
    }
}
