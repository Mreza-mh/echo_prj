import {
  Component
} from '@angular/core';
import { RouterModule } from "@angular/router";
import { HeaderComponent } from './header/header.component';
import { FooterComponent } from './footer/footer.component';
import { AiAssistantComponent } from '../panel/ai-assistant/ai-assistant.component';

@Component({
  selector: 'app-index',
  imports: [ RouterModule, HeaderComponent, FooterComponent, AiAssistantComponent],
  standalone: true,
  templateUrl: './index.component.html',
  styleUrl: './index.component.scss',
})
export class IndexComponent {}
