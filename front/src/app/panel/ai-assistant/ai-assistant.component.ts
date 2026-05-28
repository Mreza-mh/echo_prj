import { Component, inject, signal, ViewEncapsulation, HostListener } from '@angular/core';
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

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  ui?: {
    type: 'SELECT_STAFF' | 'SELECT_SERVICE' | 'SELECT_DATE' | 'SELECT_TIME' | 'CONFIRMATION';
    data: any;
  };
}

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
  ],
  templateUrl: './ai-assistant.component.html',
  styleUrls: ['./ai-assistant.component.scss'],
})
export class AiAssistantComponent {
  private indexHttp = inject(IndexHttpService);
  private sanitizer = inject(DomSanitizer);

  isOpen = signal(false);
  isLoading = signal(false);
  userInput = '';
  messages = signal<Message[]>([
    {
      role: 'assistant',
      content:
        'سلام! من دستیار هوشمند آکاری هستم. چطور می‌توانم در پیدا کردن پزشک یا رزرو نوبت به شما کمک کنم؟',
      timestamp: new Date(),
    },
  ]);

  formatMessage(msg: Message): SafeHtml {
    let content = msg.content;
    if (!content) return '';

    content = content.replace(/<think>[\s\S]*?(<\/think>|$)/gi, '');

    const uiStartIndex = content.indexOf('[UI:');
    if (uiStartIndex !== -1) {
      content = content.substring(0, uiStartIndex).trim();
    }

    content = content.replace(/\[BTN:(.*?):(.*?)\]/g, (match, label, action) => {
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

  parseUI(content: string) {
    const match = content.match(/\[UI:([A-Z_]+):([\s\S]+)\]/);
    if (match) {
      try {
        let rawData = match[2].trim();
        // تلاش برای یافتن براکت پایانی دقیق
        let openBrackets = 0;
        let cutIndex = rawData.length;

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

        const jsonData = rawData.substring(0, cutIndex);
        return {
          type: match[1] as any,
          data: JSON.parse(jsonData),
        };
      } catch (e) {
        console.error('Failed to parse UI data. Content:', match[2]);
      }
    }
    return undefined;
  }

  @HostListener('click', ['$event'])
  onChatClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (target.classList.contains('ai-btn')) {
      const action = target.getAttribute('data-action');
      if (action) {
        this.userInput = action;
        this.sendMessage();
      }
    }
  }

  toggleChat() {
    this.isOpen.update((v) => !v);
  }

  selectStaff(staff: any) {
    const displayText = `پزشک ${staff.name} را انتخاب کردم.`;
    const technicalText = `پزشک ${staff.name} (staff_id: ${staff.id}) را انتخاب کردم. حالا چه خدماتی ارائه می‌دهد؟`;
    this.sendUiMessage(displayText, technicalText);
  }

  selectService(service: any) {
    const displayText = `خدمت ${service.name} را انتخاب کردم.`;
    const technicalText = `خدمت ${service.name} (service_id: ${service.id}) را انتخاب کردم. نوبت‌های خالی را نشان بده.`;
    this.sendUiMessage(displayText, technicalText);
  }

  onDateChange(date: Date, uiData: any) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const formattedDate = `${year}-${month}-${day}`;

    const displayText = `تاریخ ${formattedDate} را انتخاب کردم.`;
    const technicalText = `برای تاریخ ${formattedDate} نوبت می‌خواهم. (staff_id: ${uiData.staff_id}, service_id: ${uiData.service_id})`;
    this.sendUiMessage(displayText, technicalText);
  }

  selectTime(slot: any, uiData: any) {
    const displayText = `ساعت ${slot.start_time} را انتخاب کردم.`;
    const technicalText = `ساعت ${slot.start_time} را برای تاریخ ${uiData.date} انتخاب کردم. (staff_id: ${uiData.staff_id}, service_id: ${uiData.service_id})`;
    this.sendUiMessage(displayText, technicalText);
  }

  confirmBooking(uiData: any) {
    const displayText = `بله، نوبت را تایید و ثبت کن.`;
    // تطابق کامل پارامترها با book_appointment
    const technicalText = `بله، نوبت را نهایی کن و ابزار book_appointment را فراخوانی کن: (staff_id: ${uiData.staff_id}, service_id: ${uiData.service_id}, date_of_turn: ${uiData.date}, start_time: ${uiData.time})`;
    this.sendUiMessage(displayText, technicalText);
  }

  private sendUiMessage(display: string, technical: string) {
    this.messages.update((msgs) => [
      ...msgs,
      {
        role: 'user',
        content: display,
        timestamp: new Date(),
      },
    ]);

    this.isLoading.set(true);

    const apiMessages = this.messages().map((m, index) => {
      if (index === this.messages().length - 1) {
        return { role: m.role, content: technical };
      }
      return { role: m.role, content: m.content };
    });

    this.indexHttp.aiChat(apiMessages).subscribe({
      next: (res: any) => this.handleAiResponse(res),
      error: (err) => this.handleAiError(err),
    });
  }

  async sendMessage() {
    if (!this.userInput.trim() || this.isLoading()) return;

    const userMsg = this.userInput;
    this.userInput = '';

    this.messages.update((msgs) => [
      ...msgs,
      {
        role: 'user',
        content: userMsg,
        timestamp: new Date(),
      },
    ]);

    this.isLoading.set(true);

    this.indexHttp
      .aiChat(this.messages().map((m) => ({ role: m.role, content: m.content })))
      .subscribe({
        next: (res: any) => this.handleAiResponse(res),
        error: (err) => this.handleAiError(err),
      });
  }

  private handleAiResponse(res: any) {
    let aiMsg = res.choices[0].message.content || '';
    const ui = this.parseUI(aiMsg);

    if (ui) {
      let prompt = '';
      switch (ui.type) {
        case 'SELECT_STAFF':
          prompt = 'لطفاً یکی از پزشکان زیر را انتخاب کنید:';
          break;
        case 'SELECT_SERVICE':
          prompt = 'لطفاً خدمت مورد نظر خود را انتخاب کنید:';
          break;
        case 'SELECT_DATE':
          prompt = 'لطفاً تاریخ مورد نظر خود را برای رزرو انتخاب کنید:';
          break;
        case 'SELECT_TIME':
          prompt = 'لطفاً یکی از ساعت‌های خالی زیر را انتخاب کنید:';
          break;
        case 'CONFIRMATION':
          prompt = 'لطفاً اطلاعات نوبت خود را تایید کنید:';
          break;
      }

      let cleanText = aiMsg.replace(/\[UI:[A-Z_]+:[\s\S]*?\]/g, '').trim();
      if (prompt && !cleanText.includes(prompt) && cleanText.length < 15) {
        aiMsg = prompt + '\n' + aiMsg;
      }
    }

    this.messages.update((msgs) => [
      ...msgs,
      {
        role: 'assistant',
        content: aiMsg,
        ui: ui,
        timestamp: new Date(),
      },
    ]);
    this.isLoading.set(false);
  }

  private handleAiError(err: any) {
    this.isLoading.set(false);
    let errorMsg = 'خطایی در ارتباط با هوش مصنوعی رخ داد.';
    if (err.error) {
      if (typeof err.error === 'string') {
        try {
          const parsed = JSON.parse(err.error);
          errorMsg = parsed.error?.message || parsed.message;
        } catch (e) {
          errorMsg = err.error;
        }
      } else {
        errorMsg = err.error.error?.message || err.error.message;
      }
    }

    this.messages.update((msgs) => [
      ...msgs,
      {
        role: 'assistant',
        content: errorMsg,
        timestamp: new Date(),
      },
    ]);
  }
}
