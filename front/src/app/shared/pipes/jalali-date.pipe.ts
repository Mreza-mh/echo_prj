import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'jalaliDate',
  standalone: true,
})
export class JalaliDatePipe implements PipeTransform {
  transform(value: string | Date | null | undefined, options?: Intl.DateTimeFormatOptions): string {
    if (!value) return '';

    const date = typeof value === 'string' ? new Date(value) : value;
    if (isNaN(date.getTime())) return typeof value === 'string' ? value : '';

    return date.toLocaleDateString('fa-IR', options || { year: 'numeric', month: 'long', day: 'numeric' });
  }
}
