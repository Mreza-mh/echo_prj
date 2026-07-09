import {
  Component,
  ElementRef,
  NgZone,
  OnDestroy,
  AfterViewInit,
  ViewChild,
  ChangeDetectorRef,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { TranslationService } from '../../../@shared/services/translation.service';
import { ThemeService } from '../../../@shared/services/theme.service';



gsap.registerPlugin(ScrollTrigger);

/**
 * ─────────────────────────────────────────────────────────────
 *  HERO CINEMATIC — CardioAI
 *
 *  یک هیروی سینمایی وابسته به اسکرول:
 *  - قلب سه‌بعدی (heart.glb) با ضربان واقعی (lub-dub) در پس‌زمینه
 *  - خط ECG که با اسکرول کشیده می‌شود
 *  - اطلاعات هیرو (عنوان، آمار، CTA) در سه صحنه روایت می‌شوند
 *
 *  صحنه ۱ (0 → 0.3):  قلب از مه بیرون می‌آید + عنوان
 *  صحنه ۲ (0.3 → 0.7): دوربین آرام drift می‌کند + آمارها با ضربان ECG
 *  صحنه ۳ (0.7 → 1):  قلب کنار می‌رود + لید و CTA + unpin
 * ─────────────────────────────────────────────────────────────
 */
@Component({
  selector: 'app-hero-cinematic',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './hero-cinematic.html',
  styleUrls: ['./hero-cinematic.scss'],
})
export class HeroCinematicComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvasHost', { static: true }) canvasHost!: ElementRef<HTMLDivElement>;
  @ViewChild('pinSection', { static: true }) pinSection!: ElementRef<HTMLElement>;
  @ViewChild('ecgPath', { static: true }) ecgPath!: ElementRef<SVGPathElement>;
  @ViewChild('introLayer', { static: true }) introLayer!: ElementRef<HTMLDivElement>;

  private zone = inject(NgZone);
  private cdr = inject(ChangeDetectorRef);
  private translationService = inject(TranslationService);
  private themeService = inject(ThemeService);

  // ── state ──
  modelLoaded = false;
  loadProgress = 0;
  modelFailed = false;
  reducedMotion = false;

  // ── three.js ──
  private renderer?: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private heartGroup = new THREE.Group();
  private keyLight!: THREE.DirectionalLight;
  private rimLight!: THREE.PointLight;
  private ambient!: THREE.AmbientLight;
  private rafId = 0;
  private clock = new THREE.Clock();
  private resizeObserver?: ResizeObserver;

  // ── gsap ──
  private tl?: gsap.core.Timeline;

  // مقادیر انیمیت‌شونده توسط تایم‌لاین (یکجا تا GC کمتر اذیت شود)
  private anim = {
    camZ: 15,
    camY: 0.6,
    heartY: 0,
    heartX: 0,
    heartRotY: -0.6,
    heartScale: 0.001,
    fogDensity: 0.16,
    keyIntensity: 0.0,
    rimIntensity: 0.0,
    bpmScale: 1, // شدت ضربان — در صحنه ۳ کمی آرام‌تر
  };

  private readonly modelPath = '/assets/models/heart.glb';
  private readonly isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  // ═══════════════════════════════ lifecycle ═══

  ngAfterViewInit(): void {
    this.reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.zone.runOutsideAngular(() => {
      this.initThree();
      this.loadHeartModel();
      if (!this.reducedMotion) {
        this.buildScrollTimeline();
      } else {
        // حالت بدون انیمیشن: همه‌چیز از اول دیده شود
        this.setStaticFinalState();
      }
      this.startRenderLoop();
    });
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.rafId);
    this.tl?.scrollTrigger?.kill();
    this.tl?.kill();
    this.resizeObserver?.disconnect();
    this.renderer?.dispose();
    this.scene?.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        obj.geometry.dispose();
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        mats.forEach((m) => m.dispose());
      }
    });
  }

  // ═══════════════════════════════ three.js ═══

  private initThree(): void {
    const host = this.canvasHost.nativeElement;

    this.scene = new THREE.Scene();
    // مه برای حس "بیرون آمدن از تاریکی" در صحنه ۱
    this.scene.fog = new THREE.FogExp2(0x000000, this.anim.fogDensity);

    this.camera = new THREE.PerspectiveCamera(38, host.clientWidth / host.clientHeight, 0.1, 100);
    this.camera.position.set(0, this.anim.camY, this.anim.camZ);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true, // پس‌زمینه شفاف — گرید ECG صفحه از پشت دیده می‌شود
      powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, this.isMobile ? 1.5 : 2));
    this.renderer.setSize(host.clientWidth, host.clientHeight);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    host.appendChild(this.renderer.domElement);

    // ── نورپردازی سینمایی ──
    this.ambient = new THREE.AmbientLight(0x223344, 0.35);
    this.scene.add(this.ambient);

    this.keyLight = new THREE.DirectionalLight(0xfff1e8, 0);
    this.keyLight.position.set(4, 6, 8);
    this.scene.add(this.keyLight);

    // نور لبه‌ای cyan — هماهنگ با پالت سایت
    this.rimLight = new THREE.PointLight(0x22d3ee, 0, 30);
    this.rimLight.position.set(-6, 2, -4);
    this.scene.add(this.rimLight);

    // نور بنفش ملایم از پایین برای عمق
    const fillLight = new THREE.PointLight(0x8b5cf6, 0.6, 25);
    fillLight.position.set(3, -4, 5);
    this.scene.add(fillLight);

    this.scene.add(this.heartGroup);

    // ── resize ──
    this.resizeObserver = new ResizeObserver(() => {
      if (!this.renderer) return;
      const w = host.clientWidth;
      const h = host.clientHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    });
    this.resizeObserver.observe(host);
  }

  private loadHeartModel(): void {
    const loader = new GLTFLoader();
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
    loader.setDRACOLoader(dracoLoader);

    loader.load(
      this.modelPath,
      (gltf) => {
        const model = gltf.scene;

        // ── center + scale (همان منطق قبلی خودت) ──
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 6.0 / maxDim;
        model.scale.setScalar(scale);
        model.position.sub(center.multiplyScalar(scale));

        model.traverse((obj) => {
          if (obj instanceof THREE.Mesh) {
            const mat = obj.material as THREE.MeshStandardMaterial;
            if (mat) {
              mat.roughness = 0.42;
              mat.metalness = 0.08;
              if (!mat.color) {
                mat.color = new THREE.Color(0x2781b1);
              } else {
                mat.color.lerp(new THREE.Color(0xff2f2f),1);
              }
            }
          }
        });

        this.heartGroup.add(model);
        this.zone.run(() => {
          this.modelLoaded = true;
          this.loadProgress = 100;
          this.cdr.markForCheck();
        });
      },
      (progress) => {
        const percent = progress.total ? Math.round((progress.loaded / progress.total) * 100) : 0;
        this.zone.run(() => {
          this.loadProgress = percent;
          this.cdr.markForCheck();
        });
      },
      (error) => {
        console.error('Failed to load heart model:', error, this.modelPath);
        this.zone.run(() => {
          this.modelFailed = true;
          this.cdr.markForCheck();
        });
      },
    );
  }

  // ═══════════════════════════════ scroll timeline ═══

  private buildScrollTimeline(): void {
    const section = this.pinSection.nativeElement;
    const rtl = this.isRTL();
    // در RTL قلب باید به «چپ» صحنه برود چون متن راست است — و برعکس
    const settleX = rtl ? -3.2 : 3.2;
    // چرخش قلب همیشه یک‌جهته پیش می‌رود (بدون برگشت) تا حس چرخش تصادفی به راست/چپ ندهد
    const settleRotY = rtl ? 1 : -2.85;

    // آماده‌سازی خط ECG برای افکت کشیده‌شدن
    const path = this.ecgPath.nativeElement;
    const pathLen = path.getTotalLength();
    path.style.strokeDasharray = `${pathLen}`;
    path.style.strokeDashoffset = `${pathLen}`;

    this.tl = gsap.timeline({
      defaults: { ease: 'power2.inOut' },
      scrollTrigger: {
        trigger: section,
        start: 'top top',
        end: this.isMobile ? '+=200%' : '+=280%',
        scrub: 1, // انیمیشن دقیقاً به اسکرول قفل می‌شود
        pin: true, // صحنه ثابت می‌ماند
        anticipatePin: 1,
        invalidateOnRefresh: true,
      },
    });

    const a = this.anim;

    // ════════ لایه ورود (0 → 0.14) — هیروی استاتیک قبلی محو و جمع می‌شود ════════
    // این لایه از همون لحظه‌ی لود صفحه دیده می‌شود تا خالی نباشد؛
    // با اولین حرکت اسکرول، جای خودش را به صحنه سینمایی می‌دهد
    gsap.set('.hc-text-col', { autoAlpha: 0 });
    this.tl
      .to(
        this.introLayer.nativeElement,
        { autoAlpha: 0, y: -30, scale: 0.98, duration: 0.14, ease: 'power2.in' },
        0,
      )
      // قاب شیشه‌ای متن سینمایی فقط بعد از محو شدن لایه ورود ظاهر می‌شود
      .to('.hc-text-col', { autoAlpha: 1, duration: 0.08 }, 0.1);

    // ════════ صحنه ۱ (0 → 0.3) — تولد ════════
    // قلب از مه و تاریکی بیرون می‌آید، دوربین جلو می‌رود، نور بالا می‌آید
    // از همون ابتدا به سمت مخالف متن می‌رود تا زیر ستون متن قرار نگیرد
    this.tl
      .to(a, { heartScale: 0.80, camZ: 11, fogDensity: 0.055, duration: 0.3 }, 0)
      .to(a, { keyIntensity: 1.6, rimIntensity: 4.5, duration: 0.3 }, 0)
      .to(a, { heartRotY: settleRotY * 0.35, heartX: settleX * 0.75, duration: 0.3 }, 0)
      // عنوان — خط به خط
      .fromTo('.hc-badge', { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 0.08 }, 0.02)
      .fromTo(
        '.hc-title-line1',
        { autoAlpha: 0, y: 40 },
        { autoAlpha: 1, y: 0, duration: 0.1 },
        0.08,
      )
      .fromTo(
        '.hc-title-line2',
        { autoAlpha: 0, y: 40 },
        { autoAlpha: 1, y: 0, duration: 0.1 },
        0.14,
      )
      .fromTo(
        '.hc-title-line3',
        { autoAlpha: 0, y: 40 },
        { autoAlpha: 1, y: 0, duration: 0.1 },
        0.2,
      )
      // خط ECG شروع به کشیده‌شدن می‌کند (تا انتهای صحنه ۲ ادامه دارد)
      .to(path, { strokeDashoffset: 0, duration: 0.62, ease: 'none' }, 0.08);

    // ════════ صحنه ۲ (0.3 → 0.7) — ضربان داده‌ها ════════
    // دوربین خیلی نرم drift می‌کند (نه orbit نمایشی)
    // هر آمار با یک "بیت" ECG ظاهر می‌شود
    this.tl
      .to(a, { camY: 1.1, heartRotY: settleRotY * 0.7, camZ: 12.5, duration: 0.4, ease: 'sine.inOut' }, 0.3)
      .fromTo(
        '.hc-stat-1',
        { autoAlpha: 0, y: 30, scale: 0.9 },
        { autoAlpha: 1, y: 0, scale: 1, duration: 0.07, ease: 'back.out(2)' },
        0.32,
      )
      .fromTo(
        '.hc-stat-2',
        { autoAlpha: 0, y: 30, scale: 0.9 },
        { autoAlpha: 1, y: 0, scale: 1, duration: 0.07, ease: 'back.out(2)' },
        0.41,
      )
      .fromTo(
        '.hc-stat-3',
        { autoAlpha: 0, y: 30, scale: 0.9 },
        { autoAlpha: 1, y: 0, scale: 1, duration: 0.07, ease: 'back.out(2)' },
        0.5,
      )
      .fromTo(
        '.hc-stat-4',
        { autoAlpha: 0, y: 30, scale: 0.9 },
        { autoAlpha: 1, y: 0, scale: 1, duration: 0.07, ease: 'back.out(2)' },
        0.59,
      )
      // کپشن کوچک وسط صحنه ۲
      .fromTo('.hc-caption', { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.06 }, 0.36)
      .to('.hc-caption', { autoAlpha: 0, duration: 0.06 }, 0.62);

    // ════════ صحنه ۳ (0.7 → 1) — استقرار ════════
    // قلب به سمت ستون تصویر می‌رود، لید + CTA + کارت اکو ظاهر می‌شوند
    this.tl
      .to(
        a,
        {
          heartX: settleX,
          heartRotY: rtl ? 0.45 : -0.45,
          heartScale: 0.52,
          camY: 0.4,
          camZ: 11,
          bpmScale: 0.55,
          duration: 0.3,
        },
        0.7,
      )
      .fromTo('.hc-lead', { autoAlpha: 0, y: 26 }, { autoAlpha: 1, y: 0, duration: 0.1 }, 0.74)
      .fromTo('.hc-actions', { autoAlpha: 0, y: 26 }, { autoAlpha: 1, y: 0, duration: 0.1 }, 0.8)
      // نشانگر اسکرول محو می‌شود
      .to('.hc-scroll-hint', { autoAlpha: 0, duration: 0.05 }, 0.72);

    // نشانگر اسکرول در ابتدای کار دیده شود
    gsap.set('.hc-scroll-hint', { autoAlpha: 1 });
  }

  /** برای prefers-reduced-motion: بدون پین و انیمیشن، حالت نهایی */
  private setStaticFinalState(): void {
    const a = this.anim;
    a.heartScale = 0.42;
    a.camZ = 11.5;
    a.fogDensity = 0.055;
    a.keyIntensity = 1.6;
    a.rimIntensity = 4.5;
    a.heartX = this.isRTL() ? -3.2 : 3.2;
    a.heartRotY = this.isRTL() ? 0.45 : -0.45;
    a.bpmScale = 0.55;
    gsap.set(
      '.hc-text-col, .hc-badge, .hc-title-line1, .hc-title-line2, .hc-title-line3, .hc-lead, .hc-actions',
      { autoAlpha: 1 },
    );
    gsap.set('.hc-scroll-hint, .hc-caption', { autoAlpha: 0 });
    gsap.set(this.introLayer.nativeElement, { autoAlpha: 0 });
    const path = this.ecgPath.nativeElement;
    path.style.strokeDasharray = 'none';
  }

  // ═══════════════════════════════ render loop ═══

  private startRenderLoop(): void {
    const loop = () => {
      this.rafId = requestAnimationFrame(loop);
      if (!this.renderer) return;

      const t = this.clock.getElapsedTime();
      const a = this.anim;

      // ── ضربان قلب: الگوی lub-dub (~64 BPM) ──
      const beatRaw = this.heartbeat(t, 64);
      const beat = beatRaw * 0.075 * a.bpmScale;
      const s = a.heartScale * (1 + beat);
      this.heartGroup.scale.setScalar(Math.max(s, 0.0001));

      // ── اعمال مقادیر تایم‌لاین ──
      this.heartGroup.position.x = a.heartX;
      this.heartGroup.position.y = a.heartY + Math.sin(t * 0.7) * 0.08; // شناور بودن خیلی ظریف
      this.heartGroup.rotation.y = a.heartRotY;

      this.camera.position.z = a.camZ;
      this.camera.position.y = a.camY;
      // نقطه نگاه دوربین ثابت است (نه دنبال قلب) تا وقتی قلب کنار می‌رود
      // واقعاً روی صفحه به یک سمت دیده شود، نه اینکه دوربین دنبالش بچرخد و وسط بماند
      this.camera.lookAt(0, 0, 0);

      this.keyLight.intensity = a.keyIntensity * (1 + beatRaw * 0.12);
      this.rimLight.intensity = a.rimIntensity * (1 + beatRaw * 0.9); // نور با ضربان می‌تپد، بدون فلیکر تند
      (this.scene.fog as THREE.FogExp2).density = a.fogDensity;

      this.renderer.render(this.scene, this.camera);
    };
    loop();
  }

  /**
   * موج ضربان واقعی: دو تپش نزدیک هم (lub-dub) و بعد استراحت.
   * خروجی 0..1
   */
  private heartbeat(t: number, bpm: number): number {
    const period = 60 / bpm;
    const phase = (t % period) / period;
    const pulse = (p: number, c: number, w: number) => Math.exp(-Math.pow((p - c) / w, 2));
    return pulse(phase, 0.12, 0.045) + 0.55 * pulse(phase, 0.28, 0.05);
  }

  // ═══════════════════════════════ helpers ═══

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  isRTL(): boolean {
    return this.translationService.getCurrentLang() === 'fa';
  }

  get isDarkMode(): boolean {
    return this.themeService.getCurrentTheme();
  }
}
