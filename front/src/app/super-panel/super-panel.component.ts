import { Component, OnInit, ViewChild, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatSidenav } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, of } from 'rxjs';
import { map, shareReplay, catchError } from 'rxjs/operators';

// Services
import { ThemeService } from '../@shared/services/theme.service';
import { TranslationService } from '../@shared/services/translation.service';
import { AuthHTTPService } from '../auth/auth-http.service';

@Component({
  selector: 'app-superpanel',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
    MatSnackBarModule,
    MatDialogModule,
    MatTooltipModule,
  ],
  templateUrl: './super-panel.component.html',
  styleUrls: ['./super-panel.component.scss'],
})
export class SuperPanelManagementComponent implements OnInit {
  @ViewChild('sidenav') sidenav!: MatSidenav;

  // Breakpoint observer for responsive design
  private breakpointObserver = inject(BreakpointObserver);
  private themeService = inject(ThemeService);
  public translationService = inject(TranslationService);
  private authHttpService = inject(AuthHTTPService);
  private router = inject(Router);

  // Responsive data
  isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset).pipe(
    map((result) => result.matches),
    shareReplay()
  );

  // User data
  currentUser$: Observable<any> = this.authHttpService.getMe().pipe(
    map(resp => resp.success ? resp.data : null),
    catchError(() => of(null)),
    shareReplay(1)
  );

  // Component state
  isSidenavOpen = true;
  sidebarCollapsed = false;
  isMobile = false;

  get isDarkMode(): boolean {
    return this.themeService.getCurrentTheme();
  }

  toggleTheme() {
    this.themeService.toggleTheme();
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  ngOnInit(): void {
    this.isHandset$.subscribe((isHandset) => {
      this.isMobile = isHandset;
      if (isHandset) {
        this.isSidenavOpen = false;
      }
    });
  }

  // Sidebar control methods
  toggleSidebar(): void {
    this.isSidenavOpen = !this.isSidenavOpen;
    if (!this.isSidenavOpen) {
      this.sidebarCollapsed = false;
    }
  }

  toggleSidebarCollapse(): void {
    if (!this.isSidenavOpen) return;
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  closeSidenav(): void {
    if (this.isMobile) {
      this.sidenav.close();
    }
  }

  logout(): void {
    localStorage.clear();
    this.router.navigate(['/auth/login']);
  }
}
