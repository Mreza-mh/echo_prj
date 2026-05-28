<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;

class EmailVerificationCode extends Mailable
{
    use Queueable, SerializesModels;

    public string $code;
    public $locale;

    /**
     * @param string $code کد تایید
     */
    public function __construct(string $code)
    {
        $this->code = $code;
    }

    public function build(): self
    {


        return $this->subject('Your Verification Code')
            ->view('emails.verification')
            ->with([
                'code' => $this->code,
                'locale' => 'en',
            ]);
    }
}
