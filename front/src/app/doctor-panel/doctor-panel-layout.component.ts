import { Component, OnInit, inject, ViewChild, DestroyRef } from '@angular/core';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { TranslationService } from '../@shared/services/translation.service';
import { ThemeService } from '../@shared/services/theme.service';
import { PanelService } from '../panel/panel.service';
import { Observable, map, shareReplay, filter, take } from 'rxjs';

@Component({
  selector: 'app-doctor-panel-layout',
  standalone: true,
  imports: [
    RouterModule,
    CommonModule,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
    MatChipsModule,
    MatTooltipModule,
  ],
  templateUrl: './doctor-panel-layout.component.html',
  styleUrls: ['./doctor-panel-layout.component.scss'],
})
export class DoctorPanelComponent implements OnInit {
  @ViewChild('sidenav') sidenav!: MatSidenav;
  private breakpointObserver = inject(BreakpointObserver);
  public translationService = inject(TranslationService);
  private themeService = inject(ThemeService);
  private panelService = inject(PanelService);
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  
  isMobile = false;
  sidenavOpened = true;
  sidebarCollapsed = false;
  currentUser$ = this.panelService.currentUser$;

  isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset).pipe(
    map((result) => result.matches),
    shareReplay(),
  );

  ngOnInit() {
    this.isHandset$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((isHandset) => {
      this.isMobile = isHandset;
      if (isHandset) {
        this.sidenavOpened = false;
      } else {
        this.sidenavOpened = true;
      }
    });

    this.activatedRoute.queryParams
      .pipe(
        filter((params) => params['orgId']),
        take(1),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((params) => {
        const orgId = params['orgId'];
        this.panelService.setActiveOrganization({ id: orgId });
      });

    this.panelService.getMe().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
  }

  toggleSidenav() {
    this.sidenavOpened = !this.sidenavOpened;
    if (this.isMobile && this.sidenavOpened) {
      this.sidenav?.open();
    } else if (this.isMobile && !this.sidenavOpened) {
      this.sidenav?.close();
    }

    if (!this.sidenavOpened) {
      this.sidebarCollapsed = false;
    }
  }

  toggleSidebarCollapse(): void {
    if (!this.sidenavOpened) return;
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  closeSidenav() {
    if (this.isMobile) {
      this.sidenavOpened = false;
      this.sidenav?.close();
    }
  }

  toggleTheme() {
    this.themeService.toggleTheme();
  }

  toggleLanguage() {
    const newLang = this.translationService.getCurrentLang() === 'en' ? 'fa' : 'en';
    this.translationService.setLanguage(newLang);
  }

  get isDarkMode(): boolean {
    return this.themeService.getCurrentTheme();
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  logout(): void {
    localStorage.clear();
    this.router.navigate(['/auth/login']);
  }
}