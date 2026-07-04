import { Component, OnInit, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { TranslationService } from '../../@shared/services/translation.service';
import { ThemeService } from '../../@shared/services/theme.service';
import { CredentialsService } from '../../auth/credentials.service';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../../auth/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    RouterModule, 
    CommonModule, 
    MatToolbarModule, 
    MatButtonModule, 
    MatIconModule, 
    MatMenuModule,
    MatDividerModule,
    MatTooltipModule
  ],
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss']
})
export class HeaderComponent implements OnInit {
  isMobile = false;
  isMenuOpen = false;
  isScrolled = false;
  isSuperAdmin = false;
  isAdmin = false;
  user: any = null;

  private breakpointObserver = inject(BreakpointObserver);
  translationService = inject(TranslationService);
  private themeService = inject(ThemeService);
  private credentialsService = inject(CredentialsService);
  private authService = inject(AuthService);
  private router = inject(Router);

  ngOnInit() {
    // Listen for scroll events to change header appearance
    if (typeof window !== 'undefined') {
      window.addEventListener('scroll', () => {
        this.isScrolled = window.scrollY > 20;
      });
    }

    this.breakpointObserver.observe([Breakpoints.Handset]).subscribe(result => {
      this.isMobile = result.matches;
      if (!this.isMobile) {
        this.isMenuOpen = false;
      }
    });

    if (this.isAuthenticated) {
      this.loadUserInfo();
    }
  }

  private loadUserInfo(): void {
    this.authService.getUserInfo().subscribe({
      next: (resp: any) => {
        if (resp && resp.success) {
          this.user = resp.data;
          this.isSuperAdmin = this.user.role === 'super_admin';
          this.isAdmin = this.user.role === 'admin' || this.isSuperAdmin;
        }
      },
      error: () => {
        this.credentialsService.setCredentials();
      }
    });
  }

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  toggleTheme() {
    this.themeService.toggleTheme();
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  get isDarkMode(): boolean {
    return this.themeService.getCurrentTheme();
  }

  get isAuthenticated(): boolean {
    return this.credentialsService.isAuthenticated();
  }

  get dashboardLink(): string {
    if (!this.user) {
      return '/dashboard'; // fallback
    }
    switch (this.user.role) {
      case 'patient':
        return '/dashboard';
      case 'doctor':
        return '/dr-panel/dashboard';
      case 'admin':
        return '/panel/dashboard';
      case 'super_admin':
        return '/super-panel';
      default:
        return '/dashboard';
    }
  }

  logout() {
    this.authService.logout().subscribe(() => {
      this.router.navigate(['/auth/login']);
    });
  }
}