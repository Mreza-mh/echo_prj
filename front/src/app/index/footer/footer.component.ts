import { Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TranslationService } from '../../@shared/services/translation.service';
import { ThemeService } from '../../@shared/services/theme.service';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterModule, MatToolbarModule, MatButtonModule, MatIconModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.scss']
})
export class FooterComponent {
  private translationService = inject(TranslationService);
  private themeService = inject(ThemeService);

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  get isDarkMode(): boolean {
    return this.themeService.getCurrentTheme();
  }
}
