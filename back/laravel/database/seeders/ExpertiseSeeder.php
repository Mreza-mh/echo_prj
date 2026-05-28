<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;

class ExpertiseSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $expertises = [
            // پزشکی
            ['title' => 'General Doctor',        'label' => 'پزشک عمومی'],
            ['title' => 'Specialist Doctor',     'label' => 'پزشک متخصص'],
            ['title' => 'Cardiologist',          'label' => 'متخصص قلب'],
            ['title' => 'Dermatologist',         'label' => 'متخصص پوست'],
            ['title' => 'Orthopedist',           'label' => 'متخصص ارتوپدی'],
            ['title' => 'Dentist',               'label' => 'دندان‌پزشک'],
            ['title' => 'Gynecologist',          'label' => 'متخصص زنان و زایمان'],
            ['title' => 'Pediatrician',          'label' => 'متخصص کودکان'],
            ['title' => 'Surgeon',               'label' => 'جراح'],
            ['title' => 'Physiotherapist',       'label' => 'فیزیوتراپیست'],

            // پیراپزشکی
            ['title' => 'Lab Technician',        'label' => 'تکنسین آزمایشگاه'],
            ['title' => 'Radiology Technician',  'label' => 'تکنسین رادیولوژی'],
            ['title' => 'Nurse',                 'label' => 'پرستار'],
            ['title' => 'Midwife',               'label' => 'مامایی'],
            ['title' => 'Nutritionist',          'label' => 'متخصص تغذیه'],
            ['title' => 'Psychologist',          'label' => 'روانشناس'],

            // سرویس‌ها
            ['title' => 'Consultation',          'label' => 'مشاوره'],
            ['title' => 'Visit',                 'label' => 'ویزیت'],
            ['title' => 'Injection',             'label' => 'تزریق'],
            ['title' => 'Blood Test',            'label' => 'آزمایش خون'],
            ['title' => 'Sample Collection',     'label' => 'نمونه‌گیری'],
            ['title' => 'Therapy Session',       'label' => 'جلسه درمان'],
            ['title' => 'Follow Up',             'label' => 'پیگیری'],
            ['title' => 'Operation Assistant',   'label' => 'کمک جراح'],

            // اداری
            ['title' => 'Receptionist',          'label' => 'مسئول پذیرش'],
            ['title' => 'Operator',              'label' => 'اپراتور'],
            ['title' => 'Admin',                 'label' => 'ادمین'],
            ['title' => 'Manager',               'label' => 'مدیر'],
        ];

        DB::table('expertises')->insert($expertises);
    }
}
