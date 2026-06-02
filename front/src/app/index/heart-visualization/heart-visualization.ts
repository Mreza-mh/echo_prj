import {
  Component, OnInit, OnDestroy, AfterViewInit,
  ViewChild, ElementRef, Input, OnChanges, SimpleChanges,
  NgZone, ChangeDetectorRef, ChangeDetectionStrategy
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';

// ─────────────────────────────────────────────────────────────────────────────
//  Interfaces
// ─────────────────────────────────────────────────────────────────────────────

export interface PatientEchoData {
  patient_info: {
    id: string;
    gender: string;
    weight: number;
    height: number;
    age?: number;
    smoker?: boolean;
    diabetic?: boolean;
    hypertensive?: boolean;
  };
  lv_edv?: number;
  lv_esv?: number;
  ef?: number;
  ivs?: number;
  lvid_d?: number;
  lvid_s?: number;
  pw?: number;
  la?: number;
  ra_volume?: number;
  la_volume?: number;
  aortic_root?: number;
  aortic_asc?: number;
  score?: number;
  category?: string;
}

interface MeasurementLabel {
  id: string;
  text: string;
  value: string;
  unit: string;
  status: 'normal' | 'warn' | 'danger' | 'info';
  // 3D position on heart model
  anchorPos: THREE.Vector3;
  // Screen position for HTML overlay
  screenX: number;
  screenY: number;
  visible: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Component
// ─────────────────────────────────────────────────────────────────────────────

@Component({
  selector: 'app-heart-visualization',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  templateUrl: './heart-visualization.html',
  styleUrls: ['./heart-visualization.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HeartVisualizationComponent
  implements OnInit, AfterViewInit, OnDestroy, OnChanges
{
  @ViewChild('heartCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('overlayEl')   overlayRef!: ElementRef<HTMLDivElement>;

  @Input() patientData: PatientEchoData | null = null;
  @Input() modelPath = '/assets/models/heart.glb';

  // Public state for template
  bmi: number | null = null;
  ef: number | null = null;
  estimatedBPM = 72;
  paused = false;
  modelLoaded = false;
  loadProgress = 0;
  activeTab: 'echo' | 'patient' = 'echo';
  measurementLabels: MeasurementLabel[] = [];

  // Three.js core
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private controls!: OrbitControls;
  private animId!: number;
  private clock = new THREE.Clock();
  
  // Heart model
  private heartModel!: THREE.Group;
  private heartMeshes: THREE.Mesh[] = [];
  
  // Measurement visualization
  private measurementGroup = new THREE.Group();
  private measurementLines: THREE.Line[] = [];
  private measurementSpheres: THREE.Mesh[] = [];

  // Resize observer
  private resizeObs!: ResizeObserver;

  constructor(private zone: NgZone, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.computeMetrics();
  }

  ngAfterViewInit() {
    this.zone.runOutsideAngular(() => {
      this.initThreeJS();
      this.loadHeartModel();
      this.setupLights();
      this.scene.add(this.measurementGroup);
      this.startRenderLoop();
      this.setupResize();
    });
  }

  ngOnChanges(c: SimpleChanges) {
    if (c['patientData'] && !c['patientData'].firstChange) {
      this.computeMetrics();
      this.updateMeasurements();
    }
  }

  ngOnDestroy() {
    cancelAnimationFrame(this.animId);
    this.renderer?.dispose();
    this.resizeObs?.disconnect();
  }

  // ─────────────────────────────────────────────────────────────
  //  Compute patient metrics
  // ─────────────────────────────────────────────────────────────

  private computeMetrics() {
    if (!this.patientData) return;
    
    const p = this.patientData.patient_info;

    // BMI
    if (p.weight && p.height) {
      const hm = p.height / 100;
      this.bmi = p.weight / (hm * hm);
    }

    // EF (Ejection Fraction)
    if (this.patientData.ef) {
      this.ef = this.patientData.ef;
    } else if (this.patientData.lv_edv && this.patientData.lv_esv) {
      const { lv_edv: edv, lv_esv: esv } = this.patientData;
      this.ef = ((edv - esv) / edv) * 100;
    } else if (this.patientData.lvid_d && this.patientData.lvid_s) {
      // Teichholz formula
      const d = this.patientData.lvid_d;
      const s = this.patientData.lvid_s;
      const edv = (7 * d ** 3) / (2.4 + d);
      const esv = (7 * s ** 3) / (2.4 + s);
      this.ef = ((edv - esv) / edv) * 100;
    }

    // BPM estimate
    let bpm = 72;
    if (p.smoker) bpm += 8;
    if (p.hypertensive) bpm += 5;
    if (p.diabetic) bpm += 3;
    if (this.ef !== null && this.ef < 40) bpm += 10;
    if (this.bmi && this.bmi > 30) bpm += 5;
    this.estimatedBPM = Math.round(bpm);

    this.buildMeasurementLabels();
    this.cdr.markForCheck();
  }

  // ─────────────────────────────────────────────────────────────
  //  Build measurement labels with 3D positions
  // ─────────────────────────────────────────────────────────────

  private buildMeasurementLabels() {
    if (!this.patientData) return;
    
    const pd = this.patientData;
    this.measurementLabels = [];

    // LV - Left Ventricle (بطن چپ) - positioned on left ventricle body
    if (pd.lvid_d) {
      const normal = pd.lvid_d <= 5.2;
      this.measurementLabels.push({
        id: 'lvid_d',
        text: 'LVIDd',
        value: pd.lvid_d.toFixed(2),
        unit: 'cm',
        status: normal ? 'normal' : 'warn',
        anchorPos: new THREE.Vector3(-1.5, -0.6, 0.8),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // LV Systole
    if (pd.lvid_s) {
      const normal = pd.lvid_s <= 3.8;
      this.measurementLabels.push({
        id: 'lvid_s',
        text: 'LVIDs',
        value: pd.lvid_s.toFixed(2),
        unit: 'cm',
        status: normal ? 'normal' : 'warn',
        anchorPos: new THREE.Vector3(-1.3, -1.8, 0.5),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // IVS (Interventricular Septum) - between LV and RV
    if (pd.ivs) {
      const hypertrophy = pd.ivs > 12;
      this.measurementLabels.push({
        id: 'ivs',
        text: 'IVS',
        value: pd.ivs.toFixed(1),
        unit: 'mm',
        status: hypertrophy ? 'warn' : 'normal',
        anchorPos: new THREE.Vector3(0.0, -0.3, 1.2),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // PW (Posterior Wall) - back wall of LV
    if (pd.pw) {
      const abnormal = pd.pw > 12 || pd.pw < 6;
      this.measurementLabels.push({
        id: 'pw',
        text: 'PW',
        value: pd.pw.toFixed(1),
        unit: 'mm',
        status: abnormal ? 'warn' : 'normal',
        anchorPos: new THREE.Vector3(-1.6, -0.8, -0.6),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // LA - Left Atrium (دهلیز چپ) - positioned on left atrium
    if (pd.la_volume) {
      const status = pd.la_volume > 34 ? 'danger' : pd.la_volume > 28 ? 'warn' : 'normal';
      this.measurementLabels.push({
        id: 'la_volume',
        text: 'LA Vol',
        value: pd.la_volume.toFixed(1),
        unit: 'mL',
        status,
        anchorPos: new THREE.Vector3(-1.2, 1.8, 0.3),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // RA - Right Atrium (دهلیز راست) - positioned on right atrium
    if (pd.ra_volume) {
      const status = pd.ra_volume > 45 ? 'warn' : 'normal';
      this.measurementLabels.push({
        id: 'ra_volume',
        text: 'RA Vol',
        value: pd.ra_volume.toFixed(1),
        unit: 'mL',
        status,
        anchorPos: new THREE.Vector3(1.2, 1.6, 0.2),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // RV - Right Ventricle (بطن راست) - if we have RV data
    if (pd.lv_edv) {
      this.measurementLabels.push({
        id: 'rv',
        text: 'RV',
        value: (pd.lv_edv * 0.6).toFixed(1),
        unit: 'mL',
        status: 'info',
        anchorPos: new THREE.Vector3(1.4, -0.4, 0.7),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // Aortic Root (ریشه آئورت)
    if (pd.aortic_root) {
      const dilated = pd.aortic_root > 3.8;
      this.measurementLabels.push({
        id: 'aortic_root',
        text: 'Ao Root',
        value: pd.aortic_root.toFixed(2),
        unit: 'cm',
        status: dilated ? 'warn' : 'normal',
        anchorPos: new THREE.Vector3(-0.4, 2.4, 0.6),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }

    // EF (Ejection Fraction) - overall heart function
    if (this.ef !== null) {
      const efStatus = this.ef >= 55 ? 'normal' : this.ef >= 40 ? 'warn' : 'danger';
      this.measurementLabels.push({
        id: 'ef',
        text: 'EF',
        value: this.ef.toFixed(0),
        unit: '%',
        status: efStatus,
        anchorPos: new THREE.Vector3(0.6, -1.4, 1.0),
        screenX: 0,
        screenY: 0,
        visible: true,
      });
    }
  }

  // ─────────────────────────────────────────────────────────────
  //  Three.js initialization
  // ─────────────────────────────────────────────────────────────

  private initThreeJS() {
    const canvas = this.canvasRef.nativeElement;
    const w = canvas.clientWidth || 600;
    const h = canvas.clientHeight || 600;

    // Renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(w, h, false);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.4;
    this.renderer.setClearColor(0x000000, 0);

    // Scene
    this.scene = new THREE.Scene();

    // Camera
    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    this.camera.position.set(0, 0, 10);

    // Controls
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 1.0;
    this.controls.minDistance = 4;
    this.controls.maxDistance = 20;
    this.controls.target.set(0, 0, 0);
  }

  // ─────────────────────────────────────────────────────────────
  //  Lighting setup
  // ─────────────────────────────────────────────────────────────

  private setupLights() {
    // Ambient light
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.6));

    // Key light (main)
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(5, 8, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.setScalar(2048);
    this.scene.add(keyLight);

    // Fill light
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
    fillLight.position.set(-5, 3, -3);
    this.scene.add(fillLight);

    // Rim light
    const rimLight = new THREE.DirectionalLight(0xff6666, 0.8);
    rimLight.position.set(0, -4, -5);
    this.scene.add(rimLight);

    // Top light
    const topLight = new THREE.DirectionalLight(0xffffff, 0.6);
    topLight.position.set(0, 10, 0);
    this.scene.add(topLight);
  }

  // ─────────────────────────────────────────────────────────────
  //  Load heart GLB model
  // ─────────────────────────────────────────────────────────────

  private loadHeartModel() {
    const loader = new GLTFLoader();
    
    // Setup Draco decoder for compressed models
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
    loader.setDRACOLoader(dracoLoader);

    console.log('🫀 Loading heart model from:', this.modelPath);

    loader.load(
      this.modelPath,
      (gltf) => {
        console.log('✅ Heart model loaded successfully');
        
        this.heartModel = gltf.scene;
        this.scene.add(this.heartModel);

        // Center and scale the model
        const box = new THREE.Box3().setFromObject(this.heartModel);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        console.log('📏 Model size:', size);
        console.log('📍 Model center:', center);
        
        // Scale to fit in view (target size: 6 units)
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 6.0 / maxDim;
        
        this.heartModel.scale.setScalar(scale);
        this.heartModel.position.sub(center.multiplyScalar(scale));
        
        // Collect all meshes
        this.heartMeshes = [];
        this.heartModel.traverse((obj) => {
          if (obj instanceof THREE.Mesh) {
            this.heartMeshes.push(obj);
            obj.castShadow = true;
            obj.receiveShadow = true;
            
            // Apply realistic material
            if (obj.material) {
              const mat = obj.material as THREE.MeshStandardMaterial;
              mat.roughness = 0.4;
              mat.metalness = 0.1;
              
              // Tint with red color for heart
              if (!mat.color) {
                mat.color = new THREE.Color(0xcc2233);
              } else {
                mat.color.lerp(new THREE.Color(0xcc2233), 0.5);
              }
            }
          }
        });

        console.log('✅ Found', this.heartMeshes.length, 'meshes in model');

        // Update measurements after model is loaded
        this.updateMeasurements();

        this.zone.run(() => {
          this.modelLoaded = true;
          this.loadProgress = 100;
          this.cdr.markForCheck();
        });
      },
      (progress) => {
        const percent = progress.total
          ? Math.round((progress.loaded / progress.total) * 100)
          : 0;
        this.zone.run(() => {
          this.loadProgress = percent;
          this.cdr.markForCheck();
        });
      },
      (error) => {
        console.error('❌ Failed to load heart model:', error);
        console.error('   Path:', this.modelPath);
        console.error('   Make sure angular.json includes src/assets in assets array');
        
        this.zone.run(() => {
          this.modelLoaded = false;
          this.loadProgress = 0;
          this.cdr.markForCheck();
        });
      }
    );
  }

  // ─────────────────────────────────────────────────────────────
  //  Update 3D measurement visualization
  // ─────────────────────────────────────────────────────────────

  private updateMeasurements() {
    if (!this.heartModel) return;

    // Clear existing measurements
    this.measurementLines.forEach(line => {
      this.measurementGroup.remove(line);
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    });
    this.measurementSpheres.forEach(sphere => {
      this.measurementGroup.remove(sphere);
      sphere.geometry.dispose();
      (sphere.material as THREE.Material).dispose();
    });
    this.measurementLines = [];
    this.measurementSpheres = [];

    // Create new measurements
    this.measurementLabels.forEach(label => {
      const color = this.getStatusColor(label.status);

      // Create sphere at anchor point
      const sphereGeo = new THREE.SphereGeometry(0.08, 16, 16);
      const sphereMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.9,
      });
      const sphere = new THREE.Mesh(sphereGeo, sphereMat);
      sphere.position.copy(label.anchorPos);
      this.measurementGroup.add(sphere);
      this.measurementSpheres.push(sphere);

      // Create glow around sphere
      const glowGeo = new THREE.SphereGeometry(0.12, 16, 16);
      const glowMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.3,
        side: THREE.BackSide,
      });
      const glow = new THREE.Mesh(glowGeo, glowMat);
      glow.position.copy(label.anchorPos);
      this.measurementGroup.add(glow);
      this.measurementSpheres.push(glow);

      // Create line extending outward
      const direction = label.anchorPos.clone().normalize();
      const lineEnd = label.anchorPos.clone().add(direction.multiplyScalar(1.5));
      
      const points = [label.anchorPos, lineEnd];
      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color,
        linewidth: 2,
        transparent: true,
        opacity: 0.7,
      });
      const line = new THREE.Line(lineGeo, lineMat);
      this.measurementGroup.add(line);
      this.measurementLines.push(line);
    });
  }

  private getStatusColor(status: string): THREE.Color {
    switch (status) {
      case 'normal': return new THREE.Color(0x3ecf7a);
      case 'warn':   return new THREE.Color(0xf0b429);
      case 'danger': return new THREE.Color(0xe84040);
      case 'info':   return new THREE.Color(0x4a7cff);
      default:       return new THREE.Color(0xffffff);
    }
  }

  // ─────────────────────────────────────────────────────────────
  //  Render loop
  // ─────────────────────────────────────────────────────────────

  private startRenderLoop() {
    const animate = () => {
      this.animId = requestAnimationFrame(animate);

      if (!this.paused) {
        this.controls.update();
        
        // Animate measurement spheres (pulsing)
        const time = this.clock.getElapsedTime();
        this.measurementSpheres.forEach((sphere, i) => {
          if (i % 2 === 1) { // Only glow spheres
            const scale = 1.0 + Math.sin(time * 3 + i) * 0.15;
            sphere.scale.setScalar(scale);
          }
        });

        // Animate measurement lines (opacity pulsing)
        this.measurementLines.forEach((line, i) => {
          const mat = line.material as THREE.LineBasicMaterial;
          mat.opacity = 0.5 + Math.sin(time * 2 + i * 0.5) * 0.2;
        });
      }

      // Update label screen positions
      this.updateLabelPositions();

      this.renderer.render(this.scene, this.camera);
    };
    animate();
  }

  // ─────────────────────────────────────────────────────────────
  //  Update label screen positions (for HTML overlay)
  // ─────────────────────────────────────────────────────────────

  private updateLabelPositions() {
    if (!this.overlayRef) return;

    const canvas = this.canvasRef.nativeElement;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    
    // Check if on mobile
    const isMobile = w < 480;

    this.measurementLabels.forEach(label => {
      // Project 3D position to screen
      const direction = label.anchorPos.clone().normalize();
      const labelPos = label.anchorPos.clone().add(direction.multiplyScalar(1.8));
      
      const vector = labelPos.clone().project(this.camera);
      
      // Check if behind camera
      const behindCamera = vector.z >= 1;
      
      // Hide labels on very small screens or if behind camera
      label.visible = !behindCamera && !isMobile;
      
      if (label.visible) {
        label.screenX = (vector.x * 0.5 + 0.5) * w;
        label.screenY = (-vector.y * 0.5 + 0.5) * h;
        
        // Keep labels within bounds
        label.screenX = Math.max(60, Math.min(w - 60, label.screenX));
        label.screenY = Math.max(40, Math.min(h - 40, label.screenY));
      }
    });

    this.cdr.detectChanges();
  }

  // ─────────────────────────────────────────────────────────────
  //  Resize handling
  // ─────────────────────────────────────────────────────────────

  private setupResize() {
    const canvas = this.canvasRef.nativeElement;
    this.resizeObs = new ResizeObserver(() => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h, false);
    });
    this.resizeObs.observe(canvas);
  }

  // ─────────────────────────────────────────────────────────────
  //  Public methods (for template)
  // ─────────────────────────────────────────────────────────────

  togglePause() {
    this.paused = !this.paused;
    this.controls.autoRotate = !this.paused;
  }

  resetCamera() {
    this.camera.position.set(0, 0, 10);
    this.controls.target.set(0, 0, 0);
    this.controls.update();
  }

  setTab(tab: 'echo' | 'patient') {
    this.activeTab = tab;
  }
}
