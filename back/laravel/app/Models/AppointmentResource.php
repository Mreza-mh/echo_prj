<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\Pivot;

class AppointmentResource extends Pivot
{
    protected $table = 'appointment_resources';

    protected $fillable = [
        'appointment_id',
        'resource_id'
    ];

    /**
     * ریلیشن به جدول Appointments
     */
    public function appointment()
    {
        return $this->belongsTo(Appointment::class, 'appointment_id');
    }

    /**
     * ریلیشن به جدول Resources
     */
    public function resource()
    {
        return $this->belongsTo(Resource::class, 'resource_id');
    }
}

