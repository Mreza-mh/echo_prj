import { Component, HostListener, ViewEncapsulation, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { IndexHttpService } from '../../index/index-http.service';
import { JalaliDatePipe } from '../../shared/pipes/jalali-date.pipe';

type ChatRole = 'user' | 'assistant' | 'system';

type UiType = 'SELECT_STAFF' | 'SELECT_SERVICE' | 'SELECT_DATE' | 'SELECT_TIME' | 'CONFIRMATION';

interface UiPayload {
  type: UiType;
  data: any;
  fullTag: string;
}

interface ChatMessage {
  role: ChatRole;
  content: string;
  timestamp: Date;
  rawContent?: string; // متن فنی که به‌جای content به API فرستاده می‌شود (برای انتخاب‌های UI)
  ui?: UiPayload;
}

const WELCOME_MESSAGE: ChatMessage = {
  role: 'assistant',
  content: 'سلام! من دستیار هوشمند اکومایند هستم. چطور می‌توانم در پیدا کردن پزشک یا رزرو نوبت به شما کمک کنم؟',
  timestamp: new Date(),
};

const UI_PROMPTS: Record<UiType, string> = {
  SELECT_STAFF: 'لطفاً یکی از پزشکان زیر را انتخاب کنید:',
  SELECT_SERVICE: 'لطفاً خدمت مورد نظر خود را انتخاب کنید:',
  SELECT_DATE: 'لطفاً تاریخ مورد نظر خود را برای رزرو انتخاب کنید:',
  SELECT_TIME: 'لطفاً یکی از ساعت‌های خالی زیر را انتخاب کنید:',
  CONFIRMATION: 'لطفاً اطلاعات نوبت خود را تایید کنید:',
};

@Component({
  selector: 'app-ai-assistant',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatCardModule,
    MatDividerModule,
    MatDatepickerModule,
    MatNativeDateModule,
    JalaliDatePipe,
  ],
  templateUrl: './ai-assistant.component.html',
  styleUrls: ['./ai-assistant.component.scss'],
})
export class AiAssistantComponent {
  private indexHttp = inject(IndexHttpService);
  private sanitizer = inject(DomSanitizer);

  isOpen = false;
  isLoading = false;
  userInput = '';

  messages: ChatMessage[] = [WELCOME_MESSAGE];
  private currentSlots: any = {};

  toggleChat(): void {
    this.isOpen = !this.isOpen;
  }

  async sendMessage(): Promise<void> {
    const text = this.userInput.trim();
    if (!text || this.isLoading) return;

    this.userInput = '';
    this.appendMessage({ role: 'user', content: text, timestamp: new Date() });
    this.sendToApi();
  }

  selectStaff(staff: any): void {
    const displayText = `پزشک ${staff.name} را انتخاب کردم.`;
    const technicalText = `پزشک ${staff.name} (staff_id: ${staff.id}) را انتخاب کردم. حالا چه خدماتی ارائه می‌دهد؟`;
    this.sendUiMessage(displayText, technicalText);
  }

  selectService(service: any): void {
    const displayText = `خدمت ${service.name} را انتخاب کردم.`;
    const technicalText = `خدمت ${service.name} (service_id: ${service.id}) را انتخاب کردم. نوبت‌های خالی را نشان بده.`;
    this.sendUiMessage(displayText, technicalText);
  }

  onDateChange(date: Date, uiData: any): void {
    const formattedDate = this.formatDate(date);
    const displayText = `تاریخ ${formattedDate} را انتخاب کردم.`;
    const technicalText = `برای تاریخ ${formattedDate} نوبت می‌خواهم. (staff_id: ${uiData.staff_id}, service_id: ${uiData.service_id})`;
    this.sendUiMessage(displayText, technicalText);
  }

  selectTime(slot: any, uiData: any): void {
    const displayText = `ساعت ${slot.start_time} را انتخاب کردم.`;
    const technicalText = `ساعت ${slot.start_time} را برای تاریخ ${uiData.date} انتخاب کردم. (staff_id: ${uiData.staff_id}, service_id: ${uiData.service_id})`;
    this.sendUiMessage(displayText, technicalText);
  }

  confirmBooking(uiData: any): void {
    const displayText = 'بله، نوبت را تایید و ثبت کن.';
    // پارامترها منطبق با AppointmentCreateRequest در بک‌اند (date_of_turn, start_time, staff_id, service_id)
    const technicalText = `بله، نوبت را نهایی کن و ابزار book_appointment را فراخوانی کن: (staff_id: ${uiData.staff_id}, service_id: ${uiData.service_id}, date_of_turn: ${uiData.date}, start_time: ${uiData.time})`;
    this.sendUiMessage(displayText, technicalText);
  }

  cancelBooking(): void {
    this.currentSlots = {};
    this.userInput = 'لغو فرآیند';
    this.sendMessage();
  }

  @HostListener('click', ['$event'])
  onChatClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    if (target.classList.contains('ai-btn')) {
      const action = target.getAttribute('data-action');
      if (action) {
        this.userInput = action;
        this.sendMessage();
      }
    }
  }

  formatMessage(msg: ChatMessage): SafeHtml {
    let content = msg.content || '';

    content = content.replace(/<think>[\s\S]*?(<\/think>|$)/gi, '');

    content = content.replace(/\[BTN:(.*?):(.*?)\]/g, (_match, label, action) => {
      return `<button class="ai-btn" data-action="${action}">${label}</button>`;
    });

    let html = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>')
      .replace(/^- (.*)/gm, '<li>$1</li>');

    if (html.includes('<li>')) {
      html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    }

    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  private sendUiMessage(display: string, technical: string): void {
    this.appendMessage({ role: 'user', content: display, rawContent: technical, timestamp: new Date() });
    this.sendToApi();
  }

  private sendToApi(): void {
    this.isLoading = true;

    // پیام اول خوش‌آمدگویی ثابت رابط کاربری است، نه بخشی از مکالمه واقعی — نباید به API ارسال شود
    const apiMessages = this.messages.slice(1).map((m) => ({
      role: m.role,
      content: m.rawContent || m.content, // ارسال دیتای فنی به‌جای متن نمایشی برای حفظ کانتکست
    }));

    this.indexHttp.aiChat(apiMessages, this.currentSlots).subscribe({
      next: (res: any) => this.handleAiResponse(res),
      error: (err: any) => this.handleAiError(err),
    });
  }

  private handleAiResponse(res: any): void {
    const aiMsg: string = res?.choices?.[0]?.message?.content || '';
    const ui = this.parseUi(aiMsg);

    // حذف هر رشته‌ای شبیه تگ [UI:...] از متن نمایشی، چه معتبر پارس شده باشد چه مدل خودش یک نمونه ناقص/جعلی نوشته باشد
    let cleanText = aiMsg.replace(/\[UI:[A-Z_]+:[\s\S]*$/g, '').trim();

    if (ui) {
      // حذف لیست آیتم‌ها از متن مدل، چون همان داده‌ها با کامپوننت UI (کارت/دکمه/تقویم) به‌صورت گرافیکی نمایش داده می‌شوند
      // و تکرارشان به‌صورت متن ساده باعث نمایش دوباره (هم متن هم گزینه) می‌شود.
      // بقیه‌ی متن مدل (خوش‌آمدگویی، توضیح، سوال) دست‌نخورده می‌ماند — پرامپت ثابت UI_PROMPTS
      // فقط زمانی اضافه می‌شود که از متن مدل چیزی باقی نمانده باشد، نه به‌عنوان تکرار.
      cleanText = cleanText.replace(/^[ \t]*[-*][ \t].*$/gm, '');
      // خط‌هایی که فقط عنوان یک لیست حذف‌شده بودند (مثل «پزشک:» یا «خدمت:» بدون ادامه) نیز حذف می‌شوند
      cleanText = cleanText.replace(/^[ \t]*\S.{0,20}:[ \t]*$/gm, '');
      cleanText = cleanText.replace(/\n{2,}/g, '\n').trim();

      if (!cleanText) {
        cleanText = UI_PROMPTS[ui.type] || '';
      }
    }

    this.appendMessage({
      role: 'assistant',
      content: cleanText, // متنی که کاربر می‌بیند، بدون سینتکس‌های فنی
      rawContent: aiMsg, // متن کامل با تگ UI، برای حفظ کانتکست در پیام‌های بعدی
      ui,
      timestamp: new Date(),
    });
    // ذخیره وضعیت اسلات‌ها برای ارسال در درخواست بعدی تا حافظه مکالمه (پزشک/خدمت/تاریخ انتخاب‌شده) حفظ شود
    this.currentSlots = res?.current_slots || {};
    this.isLoading = false;
  }

  private handleAiError(err: any): void {
    this.isLoading = false;

    let errorMsg = 'خطایی در ارتباط با هوش مصنوعی رخ داد.';
    const errBody = err?.error;

    if (typeof errBody === 'string') {
      try {
        const parsed = JSON.parse(errBody);
        errorMsg = parsed.error?.message || parsed.message || errorMsg;
      } catch {
        errorMsg = errBody;
      }
    } else if (errBody) {
      errorMsg = errBody.error?.message || errBody.message || errorMsg;
    }

    this.appendMessage({ role: 'assistant', content: errorMsg, timestamp: new Date() });
  }

  private appendMessage(msg: ChatMessage): void {
    this.messages = [...this.messages, msg];
  }

  private parseUi(content: string): UiPayload | undefined {
    // ممکن است مدل خودش یک تگ [UI:...] ناقص/جعلی در متن بنویسد و بک‌اند هم تگ واقعی را در انتها اضافه کند.
    // بنابراین همه‌ی رخدادهای [UI:...] را بررسی می‌کنیم و از آخر به اول اولین موردی که معتبر پارس شود را برمی‌گردانیم
    // (تگ بک‌اند همیشه آخرین و معتبرترین مورد است).
    const starts: number[] = [];
    const tagRegex = /\[UI:[A-Z_]+:/g;
    let m: RegExpExecArray | null;
    while ((m = tagRegex.exec(content))) {
      starts.push(m.index);
    }

    for (let s = starts.length - 1; s >= 0; s--) {
      const parsed = this.tryParseUiAt(content, starts[s]);
      if (parsed) return parsed;
    }

    return undefined;
  }

  private tryParseUiAt(content: string, startIndex: number): UiPayload | undefined {
    const match = content.slice(startIndex).match(/^\[UI:([A-Z_]+):([\s\S]+)/);
    if (!match) return undefined;

    try {
      const rawData = match[2];
      let openBrackets = 0;
      let cutIndex = -1;

      for (let i = 0; i < rawData.length; i++) {
        if (rawData[i] === '[' || rawData[i] === '{') openBrackets++;
        if (rawData[i] === ']' || rawData[i] === '}') {
          openBrackets--;
          if (openBrackets === 0) {
            cutIndex = i + 1;
            break;
          }
        }
      }

      if (cutIndex === -1) return undefined;

      const jsonData = rawData.substring(0, cutIndex);
      const fullTag = `[UI:${match[1]}:${jsonData}]`;

      return {
        type: match[1] as UiType,
        data: JSON.parse(jsonData),
        fullTag,
      };
    } catch (e) {
      return undefined;
    }
  }

  private formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
}
