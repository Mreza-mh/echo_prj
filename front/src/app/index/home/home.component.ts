import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { TranslationService } from '../../@shared/services/translation.service';
import { ThemeService } from '../../@shared/services/theme.service';
import { AuthService } from '../../auth/auth.service';
import { AuthHTTPService } from '../../auth/auth-http.service';
import { HeroCinematicComponent } from './hero-cinematic/hero-cinematic';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatChipsModule,
    HeroCinematicComponent
  ],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  private authService = inject(AuthService);
  private authhttpService = inject(AuthHTTPService);
  private translationService = inject(TranslationService);
  private themeService = inject(ThemeService);
  userRole: string | null = null;
  userName: string | null = null;
  
  // For architecture diagram interaction
  expandedDetail: string | null = null;

  // Tech Stack Data
  techStack = [
    {
      name: 'Angular 20',
      icon: 'laptop_chromebook',
      category: 'Frontend',
      className: 'angular',
      features: ['Material UI', 'PWA Support', '4 User Panels', 'Real-time Updates']
    },
    {
      name: 'Laravel 11',
      icon: 'settings_applications',
      category: 'Backend API',
      className: 'laravel',
      features: ['REST API 50+', 'JWT Auth', 'RBAC', 'Payment Integration']
    },
    {
      name: 'Python 3.11',
      icon: 'psychology',
      category: 'AI/ML Engine',
      className: 'python',
      features: ['TensorFlow', 'PyTorch U-Net++', 'OpenCV', 'Scikit-learn']
    },
    {
      name: 'Kong Gateway',
      icon: 'hub',
      category: 'API Gateway',
      className: 'kong',
      features: ['Rate Limiting', 'JWT Validation', 'Load Balancing']
    },
    {
      name: 'MongoDB',
      icon: 'storage',
      category: 'NoSQL DB',
      className: 'mongodb',
      features: ['Patient Documents', 'Visit Results', 'Dynamic Schema']
    },
    {
      name: 'Qdrant',
      icon: 'search',
      category: 'Vector DB',
      className: 'qdrant',
      features: ['Sentence-BERT', 'Intent Detection', 'Semantic Search']
    },
    {
      name: 'MySQL 8.0',
      icon: 'database',
      category: 'Relational DB',
      className: 'mysql',
      features: ['Users & Auth', 'Appointments', 'Services', 'Audit Logs']
    },
    {
      name: 'MQTT · Mosquitto',
      icon: 'sensors',
      category: 'IoT Broker',
      className: 'mqtt',
      features: ['ESP32 Heart Rate Sensor', 'Pub/Sub Messaging', 'Real-time Vitals']
    }
  ];

  ngOnInit() {
    this.loadUserInfo();
  }

  loadUserInfo() {
    this.authhttpService.getMe().subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.userRole = response.data.role;
          this.userName = response.data.name;
        }
      },
      error: () => {
        this.userRole = null;
        this.userName = null;
      },
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  isRTL(): boolean {
    return this.translationService.getCurrentLang() === 'fa';
  }

  get isDarkMode(): boolean {
    return this.themeService.getCurrentTheme();
  }

  // Architecture tree — on phones hover doesn't exist, so tapping a node
  // opens its detail in a modal instead. Desktop keeps the hover panel.
  treeModalOpen = false;
  treeModalTitle = '';
  treeModalTag = '';
  treeModalHtml = '';

  openTreeNode(event: Event): void {
    if (typeof window === 'undefined' || window.innerWidth > 640) {
      return; // desktop/tablet: the hover panel handles it
    }
    const nodeEl = event.currentTarget as HTMLElement;
    this.treeModalTitle = nodeEl.querySelector('.node-label')?.textContent?.trim() || '';
    this.treeModalTag = nodeEl.querySelector('.node-tag, .node-port')?.textContent?.trim() || '';
    this.treeModalHtml = nodeEl.querySelector('.node-hover')?.innerHTML || '';
    this.treeModalOpen = true;
  }

  closeTreeModal(): void {
    this.treeModalOpen = false;
  }

  // Interactive architecture diagram methods
  expandDetail(boxName: string): void {
    this.expandedDetail = boxName;
  }

  collapseDetail(): void {
    this.expandedDetail = null;
  }
}
