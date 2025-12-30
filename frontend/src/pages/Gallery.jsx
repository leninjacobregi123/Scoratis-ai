import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import * as THREE from 'three';
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass';
import {
  Sparkles,
  MessageCircle
} from 'lucide-react';
import { useApi } from '../hooks/useApi';

// Import subject images
import physicsImg from '../assets/subjects/physics.jpg';
import chemistryImg from '../assets/subjects/chemistry.jpg';
import biologyImg from '../assets/subjects/biology.jpg';
import mathematicsImg from '../assets/subjects/mathematics.jpg';
import computerScienceImg from '../assets/subjects/computer_science.jpg';
import englishImg from '../assets/subjects/english.jpg';
import historyImg from '../assets/subjects/history.jpg';
import philosophyImg from '../assets/subjects/philosophy.jpg';
import psychologyImg from '../assets/subjects/psychology.jpg';
import economicsImg from '../assets/subjects/economics.jpg';

// Subject image mapping
const SUBJECT_IMAGES = {
  physics: physicsImg,
  chemistry: chemistryImg,
  biology: biologyImg,
  mathematics: mathematicsImg,
  computer_science: computerScienceImg,
  english: englishImg,
  history: historyImg,
  philosophy: philosophyImg,
  psychology: psychologyImg,
  economics: economicsImg,
};

// Socrates greeting configuration
const SOCRATES_APPROACH_DISTANCE = 15; // Distance to trigger greeting

// --- Gallery Configuration ---
const HALL_WIDTH = 22;
const HALL_DEPTH = 70;  // Slightly longer for better spacing with 6 pillars
const HALL_HEIGHT = 18;

// Subject Channels - Academic learning portals
// 6 pillars at z: 24, 16, 8, 0, -8, -16 create 5 gaps
// Exactly 2 subjects between each pillar pair
const INTERACTION_SPOT_DISTANCE = 4; // Distance from wall where player must stand
const INTERACTION_SPOT_RADIUS = 1.5; // How close player needs to be to the spot

// Pillar positions for reference (6 pillars per wall)
const PILLAR_POSITIONS = [22, 14, 6, -2, -10, -18];

// Calculate exact center positions between pillars
// Pillar positions: [22, 14, 6, -2, -10, -18]
// Gap centers: (22+14)/2=18, (14+6)/2=10, (6+-2)/2=2, (-2+-10)/2=-6, (-10+-18)/2=-14
const SUBJECT_Z_POSITIONS = [18, 10, 2, -6, -14];

const SUBJECT_CHANNELS = [
  // Left Wall - Sciences & Math (5 subjects, exactly centered in each pillar gap)
  { id: 'physics', name: 'Physics', icon: '⚛️', color: '#3B82F6',
    description: 'Mechanics, thermodynamics, waves, and quantum', side: 'left', z: SUBJECT_Z_POSITIONS[0],
    spotX: -HALL_WIDTH / 2 + INTERACTION_SPOT_DISTANCE },
  { id: 'chemistry', name: 'Chemistry', icon: '🧪', color: '#10B981',
    description: 'Elements, reactions, and molecular structures', side: 'left', z: SUBJECT_Z_POSITIONS[1],
    spotX: -HALL_WIDTH / 2 + INTERACTION_SPOT_DISTANCE },
  { id: 'biology', name: 'Biology', icon: '🧬', color: '#EC4899',
    description: 'Life sciences, cells, genetics, and ecosystems', side: 'left', z: SUBJECT_Z_POSITIONS[2],
    spotX: -HALL_WIDTH / 2 + INTERACTION_SPOT_DISTANCE },
  { id: 'mathematics', name: 'Mathematics', icon: '📐', color: '#8B5CF6',
    description: 'Algebra, calculus, geometry, and logic', side: 'left', z: SUBJECT_Z_POSITIONS[3],
    spotX: -HALL_WIDTH / 2 + INTERACTION_SPOT_DISTANCE },
  { id: 'computer_science', name: 'Computer Science', icon: '💻', color: '#06B6D4',
    description: 'Programming, algorithms, and technology', side: 'left', z: SUBJECT_Z_POSITIONS[4],
    spotX: -HALL_WIDTH / 2 + INTERACTION_SPOT_DISTANCE },

  // Right Wall - Humanities & Social Sciences (5 subjects, exactly centered in each pillar gap)
  { id: 'english', name: 'English', icon: '📚', color: '#F59E0B',
    description: 'Literature, writing, and language arts', side: 'right', z: SUBJECT_Z_POSITIONS[0],
    spotX: HALL_WIDTH / 2 - INTERACTION_SPOT_DISTANCE },
  { id: 'history', name: 'History', icon: '🏛️', color: '#78716C',
    description: 'World history, civilizations, and events', side: 'right', z: SUBJECT_Z_POSITIONS[1],
    spotX: HALL_WIDTH / 2 - INTERACTION_SPOT_DISTANCE },
  { id: 'philosophy', name: 'Philosophy', icon: '🤔', color: '#6366F1',
    description: 'Ethics, logic, metaphysics, and wisdom', side: 'right', z: SUBJECT_Z_POSITIONS[2],
    spotX: HALL_WIDTH / 2 - INTERACTION_SPOT_DISTANCE },
  { id: 'psychology', name: 'Psychology', icon: '🧠', color: '#F472B6',
    description: 'Mind, behavior, and human cognition', side: 'right', z: SUBJECT_Z_POSITIONS[3],
    spotX: HALL_WIDTH / 2 - INTERACTION_SPOT_DISTANCE },
  { id: 'economics', name: 'Economics', icon: '📊', color: '#22C55E',
    description: 'Markets, finance, and economic systems', side: 'right', z: SUBJECT_Z_POSITIONS[4],
    spotX: HALL_WIDTH / 2 - INTERACTION_SPOT_DISTANCE },
];

const Gallery = () => {
  const navigate = useNavigate();
  const api = useApi();

  const [focusEntity, setFocusEntity] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [modelStatus, setModelStatus] = useState('loading');
  const [loadingPhase, setLoadingPhase] = useState('loading'); // 'loading' | 'ready' | 'zooming' | 'gallery'

  // Session choice modal for subjects
  const [showSessionChoice, setShowSessionChoice] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState(null);

  // Real loading progress tracking
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingStatus, setLoadingStatus] = useState('Initializing...');
  const [loadingStages, setLoadingStages] = useState({
    backend: false,
    subjects: false,
    characterModel: false,
    socratesModel: false,
    scene: false
  });
  const [minTimeElapsed, setMinTimeElapsed] = useState(false);

  // Socrates greeting state
  const [hasGreeted, setHasGreeted] = useState(false);
  const [showWelcomeDialog, setShowWelcomeDialog] = useState(false);
  const [greetingText, setGreetingText] = useState('');

  // Calculate total progress from stages
  useEffect(() => {
    const stages = loadingStages;
    let progress = 0;
    if (stages.backend) progress += 15;
    if (stages.subjects) progress += 15;
    if (stages.characterModel) progress += 30;
    if (stages.socratesModel) progress += 25;
    if (stages.scene) progress += 15;
    setLoadingProgress(progress);
  }, [loadingStages]);

  // Minimum display time (7 seconds for reading quote)
  useEffect(() => {
    const timer = setTimeout(() => {
      setMinTimeElapsed(true);
    }, 7000);
    return () => clearTimeout(timer);
  }, []);

  // Transition logic - only when fully loaded AND min time elapsed
  useEffect(() => {
    const allLoaded = loadingProgress >= 100;

    if (allLoaded && minTimeElapsed && loadingPhase === 'loading') {
      // Move to ready phase
      setLoadingPhase('ready');

      // After 1 second in ready, start zooming
      setTimeout(() => {
        setLoadingPhase('zooming');
      }, 1000);

      // After zoom animation, show gallery
      setTimeout(() => {
        setLoadingPhase('gallery');
      }, 2500);
    }
  }, [loadingProgress, minTimeElapsed, loadingPhase]);

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      setLoadingStatus('Connecting to server...');
      try {
        await api.get('/health');
        setLoadingStages(prev => ({ ...prev, backend: true }));
        setLoadingStatus('Server connected');
      } catch (error) {
        console.error('Backend health check failed:', error);
        // Still mark as done to not block loading
        setLoadingStages(prev => ({ ...prev, backend: true }));
      }
    };
    checkBackend();
  }, []);

  const containerRef = useRef();
  const greetingTriggeredRef = useRef(false);
  const stateRef = useRef({
    scene: null, camera: null, renderer: null, player: null,
    clock: new THREE.Clock(), keys: {}, paintings: [], socrates: null,
    vel: new THREE.Vector3(0, 0, 0),
    mixer: null,
    fbxModel: null
  });

  // Load subject channels (static data - instant)
  useEffect(() => {
    setLoadingStatus('Loading subject channels...');
    // Subjects are defined statically, so mark as loaded immediately
    setLoadingStages(prev => ({ ...prev, subjects: true }));
    setLoadingStatus('Subjects loaded');
    setIsLoading(false);
  }, []);

  // Trigger Socrates greeting when player approaches
  const triggerSocratesGreeting = async () => {
    if (hasGreeted || showWelcomeDialog) return;

    setHasGreeted(true);
    setShowWelcomeDialog(true);

    // Set default greeting text
    setGreetingText("Ah, a seeker of wisdom approaches. Welcome, young philosopher. I am Socrates, and I have been expecting you. Tell me... are you ready to question everything you think you know?");
  };

  // Handle entering chat with Socrates
  const handleEnterChat = () => {
    setShowWelcomeDialog(false);
    navigate('/app/scoratis');
  };

  // Handle declining to enter
  const handleDeclineChat = () => {
    setShowWelcomeDialog(false);
    // Allow greeting again after some time
    setTimeout(() => setHasGreeted(false), 30000);
  };

  // Initialize Three.js scene
  useEffect(() => {
    if (isLoading) return;

    // 1. Scene & Camera (Ethereal heavenly atmosphere)
    const scene = new THREE.Scene();

    // Simple neutral background - realistic interior ambient
    scene.background = new THREE.Color(0xf0ebe3);

    // No fog - keep Socrates and all elements crisp and clear

    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance"
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;  // Slightly reduced for natural look

    if (containerRef.current) {
      containerRef.current.innerHTML = '';
      containerRef.current.appendChild(renderer.domElement);
    }

    // 2. Lighting - Natural museum lighting
    const amb = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(amb);

    // Main overhead light - natural daylight feel
    const mainLight = new THREE.DirectionalLight(0xfff8f0, 0.9);
    mainLight.position.set(0, 25, -10);
    mainLight.castShadow = true;
    mainLight.shadow.mapSize.width = 2048;
    mainLight.shadow.mapSize.height = 2048;
    mainLight.shadow.camera.far = 100;
    mainLight.shadow.bias = -0.0001;
    scene.add(mainLight);

    // Soft fill light from side
    const fillLight1 = new THREE.DirectionalLight(0xfff5e8, 0.3);
    fillLight1.position.set(-15, 12, 20);
    scene.add(fillLight1);

    // Warm fill from front
    const fillLight2 = new THREE.DirectionalLight(0xfff5e6, 0.35);
    fillLight2.position.set(0, 8, 40);
    scene.add(fillLight2);

    // Hemisphere light - subtle sky to ground gradient
    const hemiLight = new THREE.HemisphereLight(0xf5f5f5, 0xebe5d8, 0.5);
    scene.add(hemiLight);

    // 3. Environment (Gallery) - Professional Museum Style
    const galleryGroup = new THREE.Group();

    // Create subtle marble texture procedurally
    const marbleCanvas = document.createElement('canvas');
    marbleCanvas.width = 512;
    marbleCanvas.height = 512;
    const marbleCtx = marbleCanvas.getContext('2d');

    // Base color
    marbleCtx.fillStyle = '#f5f0e8';
    marbleCtx.fillRect(0, 0, 512, 512);

    // Add subtle veins
    marbleCtx.strokeStyle = 'rgba(200, 195, 185, 0.3)';
    marbleCtx.lineWidth = 1;
    for (let i = 0; i < 20; i++) {
      marbleCtx.beginPath();
      marbleCtx.moveTo(Math.random() * 512, Math.random() * 512);
      marbleCtx.bezierCurveTo(
        Math.random() * 512, Math.random() * 512,
        Math.random() * 512, Math.random() * 512,
        Math.random() * 512, Math.random() * 512
      );
      marbleCtx.stroke();
    }

    // Add noise/grain
    const imageData = marbleCtx.getImageData(0, 0, 512, 512);
    for (let i = 0; i < imageData.data.length; i += 4) {
      const noise = (Math.random() - 0.5) * 8;
      imageData.data[i] += noise;
      imageData.data[i + 1] += noise;
      imageData.data[i + 2] += noise;
    }
    marbleCtx.putImageData(imageData, 0, 0);

    const marbleTexture = new THREE.CanvasTexture(marbleCanvas);
    marbleTexture.wrapS = THREE.RepeatWrapping;
    marbleTexture.wrapT = THREE.RepeatWrapping;
    marbleTexture.repeat.set(4, 16);

    // Museum Marble Checkered Floor
    const floorTileSize = 2.5;
    const tilesX = Math.ceil(HALL_WIDTH / floorTileSize);
    const tilesZ = Math.ceil(HALL_DEPTH / floorTileSize);

    // Create marble textures for light and dark tiles
    const createMarbleTileTexture = (baseColor, veinColor) => {
      const tileCanvas = document.createElement('canvas');
      tileCanvas.width = 256;
      tileCanvas.height = 256;
      const ctx = tileCanvas.getContext('2d');

      // Base color
      ctx.fillStyle = baseColor;
      ctx.fillRect(0, 0, 256, 256);

      // Add marble veins
      ctx.strokeStyle = veinColor;
      ctx.lineWidth = 0.5;
      for (let i = 0; i < 8; i++) {
        ctx.beginPath();
        ctx.moveTo(Math.random() * 256, Math.random() * 256);
        ctx.bezierCurveTo(
          Math.random() * 256, Math.random() * 256,
          Math.random() * 256, Math.random() * 256,
          Math.random() * 256, Math.random() * 256
        );
        ctx.stroke();
      }

      // Subtle noise for realism
      const imageData = ctx.getImageData(0, 0, 256, 256);
      for (let i = 0; i < imageData.data.length; i += 4) {
        const noise = (Math.random() - 0.5) * 10;
        imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + noise));
        imageData.data[i + 1] = Math.min(255, Math.max(0, imageData.data[i + 1] + noise));
        imageData.data[i + 2] = Math.min(255, Math.max(0, imageData.data[i + 2] + noise));
      }
      ctx.putImageData(imageData, 0, 0);

      const texture = new THREE.CanvasTexture(tileCanvas);
      texture.wrapS = THREE.ClampToEdgeWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      return texture;
    };

    const lightMarbleTexture = createMarbleTileTexture('#f8f4ec', 'rgba(180, 175, 165, 0.4)');
    const darkMarbleTexture = createMarbleTileTexture('#2a2520', 'rgba(60, 55, 50, 0.5)');

    const lightTileMat = new THREE.MeshStandardMaterial({
      map: lightMarbleTexture,
      roughness: 0.45,  // More matte for realistic worn marble
      metalness: 0.0
    });

    const darkTileMat = new THREE.MeshStandardMaterial({
      map: darkMarbleTexture,
      roughness: 0.5,
      metalness: 0.0
    });

    const floorGroup = new THREE.Group();
    const tileGeo = new THREE.PlaneGeometry(floorTileSize - 0.02, floorTileSize - 0.02);

    for (let x = 0; x < tilesX; x++) {
      for (let z = 0; z < tilesZ; z++) {
        const isLight = (x + z) % 2 === 0;
        const tile = new THREE.Mesh(tileGeo, isLight ? lightTileMat : darkTileMat);
        tile.rotation.x = -Math.PI / 2;
        tile.position.set(
          -HALL_WIDTH / 2 + floorTileSize / 2 + x * floorTileSize,
          0,
          -HALL_DEPTH / 2 + floorTileSize / 2 + z * floorTileSize
        );
        tile.receiveShadow = true;
        floorGroup.add(tile);
      }
    }

    // Floor base underneath tiles
    const floorBase = new THREE.Mesh(
      new THREE.PlaneGeometry(HALL_WIDTH + 2, HALL_DEPTH + 2),
      new THREE.MeshStandardMaterial({ color: 0x1a1815, roughness: 0.9 })
    );
    floorBase.rotation.x = -Math.PI / 2;
    floorBase.position.y = -0.01;
    floorGroup.add(floorBase);

    galleryGroup.add(floorGroup);

    // Gallery hall lighting - warm spotlights along the walls
    const galleryLightPositions = [-30, -10, 10, 30];
    galleryLightPositions.forEach(z => {
      // Left side light
      const leftLight = new THREE.PointLight(0xfff5e6, 0.8, 20);
      leftLight.position.set(-HALL_WIDTH/2 + 2, HALL_HEIGHT - 2, z);
      scene.add(leftLight);

      // Right side light
      const rightLight = new THREE.PointLight(0xfff5e6, 0.8, 20);
      rightLight.position.set(HALL_WIDTH/2 - 2, HALL_HEIGHT - 2, z);
      scene.add(rightLight);
    });

    // Create realistic plaster wall texture with subtle variations
    const wallTextureCanvas = document.createElement('canvas');
    wallTextureCanvas.width = 512;
    wallTextureCanvas.height = 512;
    const wallTexCtx = wallTextureCanvas.getContext('2d');

    // Base plaster color
    wallTexCtx.fillStyle = '#f5f2ed';
    wallTexCtx.fillRect(0, 0, 512, 512);

    // Add subtle noise for plaster texture
    const wallImageData = wallTexCtx.getImageData(0, 0, 512, 512);
    for (let i = 0; i < wallImageData.data.length; i += 4) {
      const noise = (Math.random() - 0.5) * 12;
      wallImageData.data[i] = Math.min(255, Math.max(0, wallImageData.data[i] + noise));
      wallImageData.data[i + 1] = Math.min(255, Math.max(0, wallImageData.data[i + 1] + noise));
      wallImageData.data[i + 2] = Math.min(255, Math.max(0, wallImageData.data[i + 2] + noise));
    }
    wallTexCtx.putImageData(wallImageData, 0, 0);

    // Add very subtle darker patches for depth
    wallTexCtx.globalAlpha = 0.03;
    for (let i = 0; i < 20; i++) {
      wallTexCtx.fillStyle = '#d0ccc5';
      wallTexCtx.beginPath();
      wallTexCtx.ellipse(
        Math.random() * 512,
        Math.random() * 512,
        Math.random() * 80 + 30,
        Math.random() * 60 + 20,
        Math.random() * Math.PI,
        0, Math.PI * 2
      );
      wallTexCtx.fill();
    }
    wallTexCtx.globalAlpha = 1;

    const wallTexture = new THREE.CanvasTexture(wallTextureCanvas);
    wallTexture.wrapS = THREE.RepeatWrapping;
    wallTexture.wrapT = THREE.RepeatWrapping;
    wallTexture.repeat.set(8, 2);

    const wallMat = new THREE.MeshStandardMaterial({
      map: wallTexture,
      roughness: 0.92,
      metalness: 0.0,
      envMapIntensity: 0.3
    });
    const sideWallGeo = new THREE.PlaneGeometry(HALL_DEPTH, HALL_HEIGHT);

    const lWall = new THREE.Mesh(sideWallGeo, wallMat);
    lWall.rotation.y = Math.PI / 2;
    lWall.position.set(-HALL_WIDTH / 2, HALL_HEIGHT / 2, 0);
    galleryGroup.add(lWall);

    const rWall = new THREE.Mesh(sideWallGeo, wallMat);
    rWall.rotation.y = -Math.PI / 2;
    rWall.position.set(HALL_WIDTH / 2, HALL_HEIGHT / 2, 0);
    galleryGroup.add(rWall);

    // Back wall - use dark material for cosmic backdrop to show properly
    const backWallMat = new THREE.MeshBasicMaterial({ color: 0x000008 });
    const backWall = new THREE.Mesh(new THREE.PlaneGeometry(HALL_WIDTH, HALL_HEIGHT), backWallMat);
    backWall.position.set(0, HALL_HEIGHT / 2, -HALL_DEPTH / 2);
    galleryGroup.add(backWall);

    // ====== SOCRATES BACKDROP - Cosmic Celestial Portal ======
    const alcoveGroup = new THREE.Group();
    const alcoveZ = -HALL_DEPTH / 2 + 0.5;

    // ====== STUNNING COSMIC GALAXY BACKDROP ======
    const backdropCanvas = document.createElement('canvas');
    backdropCanvas.width = 2048;
    backdropCanvas.height = 2048;
    const bdCtx = backdropCanvas.getContext('2d');

    // Deep space background - dark void with subtle blue tint
    const spaceGradient = bdCtx.createRadialGradient(1024, 1024, 0, 1024, 1024, 1200);
    spaceGradient.addColorStop(0, '#0a0a1a');
    spaceGradient.addColorStop(0.3, '#050510');
    spaceGradient.addColorStop(0.6, '#020208');
    spaceGradient.addColorStop(1, '#000005');
    bdCtx.fillStyle = spaceGradient;
    bdCtx.fillRect(0, 0, 2048, 2048);

    // Nebula clouds - multiple layers of cosmic gas
    const drawNebula = (cx, cy, radius, colors, opacity) => {
      for (let layer = 0; layer < 5; layer++) {
        const layerRadius = radius * (1 - layer * 0.15);
        const nebGradient = bdCtx.createRadialGradient(cx, cy, 0, cx, cy, layerRadius);
        nebGradient.addColorStop(0, colors[0]);
        nebGradient.addColorStop(0.3, colors[1]);
        nebGradient.addColorStop(0.6, colors[2]);
        nebGradient.addColorStop(1, 'transparent');
        bdCtx.globalAlpha = opacity * (1 - layer * 0.2);
        bdCtx.fillStyle = nebGradient;
        bdCtx.beginPath();
        bdCtx.arc(cx, cy, layerRadius, 0, Math.PI * 2);
        bdCtx.fill();
      }
    };

    // Purple/violet nebula (primary)
    drawNebula(1024, 900, 800, ['rgba(138, 43, 226, 0.4)', 'rgba(75, 0, 130, 0.3)', 'rgba(48, 25, 88, 0.1)'], 0.6);
    // Blue nebula accent
    drawNebula(700, 700, 500, ['rgba(30, 144, 255, 0.3)', 'rgba(0, 100, 200, 0.2)', 'rgba(0, 50, 100, 0.1)'], 0.5);
    // Pink/magenta accent
    drawNebula(1300, 600, 450, ['rgba(255, 20, 147, 0.25)', 'rgba(199, 21, 133, 0.15)', 'rgba(139, 0, 139, 0.05)'], 0.4);
    // Teal/cyan accent
    drawNebula(850, 1200, 400, ['rgba(0, 255, 255, 0.2)', 'rgba(0, 139, 139, 0.1)', 'rgba(0, 100, 100, 0.05)'], 0.35);

    // Swirling galaxy arms effect
    bdCtx.globalAlpha = 0.3;
    for (let arm = 0; arm < 4; arm++) {
      const baseAngle = (arm / 4) * Math.PI * 2;
      for (let i = 0; i < 200; i++) {
        const t = i / 200;
        const spiralRadius = 100 + t * 700;
        const angle = baseAngle + t * Math.PI * 3;
        const x = 1024 + Math.cos(angle) * spiralRadius;
        const y = 900 + Math.sin(angle) * spiralRadius * 0.6;
        const size = 2 + Math.random() * 4;
        const brightness = 0.3 + Math.random() * 0.4;

        bdCtx.beginPath();
        bdCtx.arc(x + (Math.random() - 0.5) * 30, y + (Math.random() - 0.5) * 30, size, 0, Math.PI * 2);
        bdCtx.fillStyle = `rgba(200, 180, 255, ${brightness})`;
        bdCtx.fill();
      }
    }

    // Static stars - varying sizes and colors
    bdCtx.globalAlpha = 1;
    const starColors = ['#ffffff', '#ffe4c4', '#add8e6', '#ffd700', '#e6e6fa'];
    for (let i = 0; i < 800; i++) {
      const x = Math.random() * 2048;
      const y = Math.random() * 2048;
      const size = Math.random() < 0.9 ? Math.random() * 1.5 : Math.random() * 3 + 1;
      const color = starColors[Math.floor(Math.random() * starColors.length)];
      const alpha = 0.4 + Math.random() * 0.6;

      bdCtx.beginPath();
      bdCtx.arc(x, y, size, 0, Math.PI * 2);
      bdCtx.fillStyle = color;
      bdCtx.globalAlpha = alpha;
      bdCtx.fill();

      // Add glow to larger stars
      if (size > 2) {
        const starGlow = bdCtx.createRadialGradient(x, y, 0, x, y, size * 4);
        starGlow.addColorStop(0, color);
        starGlow.addColorStop(0.5, `${color}44`);
        starGlow.addColorStop(1, 'transparent');
        bdCtx.globalAlpha = 0.3;
        bdCtx.fillStyle = starGlow;
        bdCtx.beginPath();
        bdCtx.arc(x, y, size * 4, 0, Math.PI * 2);
        bdCtx.fill();
      }
    }
    bdCtx.globalAlpha = 1;

    // Central cosmic eye / portal center - golden wisdom glow
    const portalCenter = bdCtx.createRadialGradient(1024, 900, 0, 1024, 900, 250);
    portalCenter.addColorStop(0, 'rgba(255, 215, 0, 0.6)');
    portalCenter.addColorStop(0.2, 'rgba(255, 180, 50, 0.4)');
    portalCenter.addColorStop(0.5, 'rgba(255, 140, 0, 0.2)');
    portalCenter.addColorStop(0.8, 'rgba(138, 43, 226, 0.1)');
    portalCenter.addColorStop(1, 'transparent');
    bdCtx.fillStyle = portalCenter;
    bdCtx.beginPath();
    bdCtx.arc(1024, 900, 250, 0, Math.PI * 2);
    bdCtx.fill();

    // Divine light rays emanating from center
    bdCtx.globalAlpha = 0.15;
    const rayCount = 48;
    for (let i = 0; i < rayCount; i++) {
      const angle = (i / rayCount) * Math.PI * 2;
      const rayGradient = bdCtx.createLinearGradient(
        1024, 900,
        1024 + Math.cos(angle) * 900, 900 + Math.sin(angle) * 900
      );
      rayGradient.addColorStop(0, 'rgba(255, 215, 0, 0.8)');
      rayGradient.addColorStop(0.3, 'rgba(255, 180, 100, 0.3)');
      rayGradient.addColorStop(1, 'transparent');

      bdCtx.beginPath();
      bdCtx.moveTo(1024, 900);
      const spread = 0.025;
      bdCtx.lineTo(
        1024 + Math.cos(angle - spread) * 1000,
        900 + Math.sin(angle - spread) * 1000
      );
      bdCtx.lineTo(
        1024 + Math.cos(angle + spread) * 1000,
        900 + Math.sin(angle + spread) * 1000
      );
      bdCtx.closePath();
      bdCtx.fillStyle = rayGradient;
      bdCtx.fill();
    }
    bdCtx.globalAlpha = 1;

    const backdropTexture = new THREE.CanvasTexture(backdropCanvas);
    const backdropMat = new THREE.MeshBasicMaterial({ map: backdropTexture, depthWrite: false });
    const backdrop = new THREE.Mesh(
      new THREE.PlaneGeometry(HALL_WIDTH + 4, HALL_HEIGHT + 4),
      backdropMat
    );
    backdrop.position.set(0, HALL_HEIGHT / 2, alcoveZ + 0.5);
    backdrop.renderOrder = 1;
    alcoveGroup.add(backdrop);

    // ====== STUNNING COSMIC SPACE EFFECTS ======

    // 1. REALISTIC STAR FIELD using Points (GPU-efficient)
    const starFieldGeometry = new THREE.BufferGeometry();
    const starCount = 2000;
    const starPositions = new Float32Array(starCount * 3);
    const starFieldColors = new Float32Array(starCount * 3);
    const starSizes = new Float32Array(starCount);

    // Star color palette (realistic star colors)
    const starColorPalette = [
      new THREE.Color(0xffffff), // White
      new THREE.Color(0xfff4e8), // Warm white
      new THREE.Color(0xe8f4ff), // Cool white
      new THREE.Color(0xffd700), // Yellow (sun-like)
      new THREE.Color(0x87ceeb), // Light blue
      new THREE.Color(0xffb347), // Orange giant
      new THREE.Color(0xff6b6b), // Red giant
      new THREE.Color(0x9370db), // Purple
    ];

    for (let i = 0; i < starCount; i++) {
      // Spread stars across a wide dome behind Socrates
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI * 0.6;
      const r = 12 + Math.random() * 25;

      starPositions[i * 3] = Math.sin(phi) * Math.cos(theta) * r;
      starPositions[i * 3 + 1] = Math.abs(Math.cos(phi)) * r * 0.8 + 2;
      starPositions[i * 3 + 2] = alcoveZ - 5 - Math.sin(phi) * Math.abs(Math.sin(theta)) * r * 0.3;

      // Random star color
      const color = starColorPalette[Math.floor(Math.random() * starColorPalette.length)];
      starFieldColors[i * 3] = color.r;
      starFieldColors[i * 3 + 1] = color.g;
      starFieldColors[i * 3 + 2] = color.b;

      // Varied star sizes (most small, few large)
      starSizes[i] = Math.random() < 0.95 ? 0.5 + Math.random() * 1.5 : 2 + Math.random() * 3;
    }

    starFieldGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    starFieldGeometry.setAttribute('color', new THREE.BufferAttribute(starFieldColors, 3));
    starFieldGeometry.setAttribute('size', new THREE.BufferAttribute(starSizes, 1));

    const starFieldMaterial = new THREE.PointsMaterial({
      size: 0.15,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
    });

    const starField = new THREE.Points(starFieldGeometry, starFieldMaterial);
    alcoveGroup.add(starField);
    stateRef.current.starField = starField;

    // 2. BLINKING STARS (realistic twinkling effect)
    const featuredStarsGroup = new THREE.Group();
    const featuredStars = [];

    // Create shared star texture
    const starTexture = new THREE.CanvasTexture((() => {
      const canvas = document.createElement('canvas');
      canvas.width = 64;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
      gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
      gradient.addColorStop(0.1, 'rgba(255, 255, 255, 0.9)');
      gradient.addColorStop(0.3, 'rgba(220, 220, 255, 0.4)');
      gradient.addColorStop(1, 'rgba(100, 100, 200, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 64, 64);
      return canvas;
    })());

    // Create 60 blinking stars for realistic effect
    for (let i = 0; i < 60; i++) {
      const starSprite = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: starTexture,
          transparent: true,
          blending: THREE.AdditiveBlending,
          color: starColorPalette[Math.floor(Math.random() * starColorPalette.length)],
        })
      );

      const x = (Math.random() - 0.5) * 35;
      const y = 2 + Math.random() * 16;
      const z = alcoveZ - 1 - Math.random() * 12;

      starSprite.position.set(x, y, z);
      const baseScale = 0.2 + Math.random() * 0.6;
      starSprite.scale.set(baseScale, baseScale, 1);

      // Varied blinking patterns for realism
      const blinkType = Math.floor(Math.random() * 3); // 0=slow, 1=medium, 2=fast flicker
      starSprite.userData = {
        twinkleSpeed: blinkType === 0 ? 0.3 + Math.random() * 0.5 :
                      blinkType === 1 ? 1 + Math.random() * 2 :
                      3 + Math.random() * 4,
        twinklePhase: Math.random() * Math.PI * 2,
        baseScale: baseScale,
        baseOpacity: 0.6 + Math.random() * 0.4,
        blinkType: blinkType,
        // Random "flicker" moments
        nextFlicker: Math.random() * 5,
        flickering: false,
      };

      featuredStars.push(starSprite);
      featuredStarsGroup.add(starSprite);
    }

    alcoveGroup.add(featuredStarsGroup);
    stateRef.current.featuredStars = featuredStars;

    // 3. SHOOTING STARS / METEORS
    const shootingStarsGroup = new THREE.Group();
    const shootingStars = [];

    for (let i = 0; i < 5; i++) {
      const meteorGeometry = new THREE.BufferGeometry();
      const trailLength = 15;
      const positions = new Float32Array(trailLength * 3);
      const opacities = new Float32Array(trailLength);

      for (let j = 0; j < trailLength; j++) {
        positions[j * 3] = 0;
        positions[j * 3 + 1] = 0;
        positions[j * 3 + 2] = 0;
        opacities[j] = 1 - j / trailLength;
      }

      meteorGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

      const meteorMaterial = new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.2,
        transparent: true,
        opacity: 0,
        blending: THREE.AdditiveBlending,
      });

      const meteor = new THREE.Points(meteorGeometry, meteorMaterial);
      meteor.userData = {
        active: false,
        progress: 0,
        startX: 0,
        startY: 0,
        startZ: 0,
        dirX: 0,
        dirY: 0,
        dirZ: 0,
        speed: 0,
        nextTrigger: Math.random() * 10 + 5,
        trailLength: trailLength,
      };

      shootingStars.push(meteor);
      shootingStarsGroup.add(meteor);
    }

    alcoveGroup.add(shootingStarsGroup);
    stateRef.current.shootingStars = shootingStars;

    // Nebula clouds removed for cleaner look

    // 5. BEAUTIFUL ROTATING GALAXY (centered behind Socrates head, facing audience)
    const galaxyGroup = new THREE.Group();
    // Position behind and above Socrates head level
    galaxyGroup.position.set(0, 10, alcoveZ - 2);

    const galaxyGeometry = new THREE.BufferGeometry();
    const galaxyCount = 20000; // Dense galaxy
    const galaxyPositions = new Float32Array(galaxyCount * 3);
    const galaxyColors = new Float32Array(galaxyCount * 3);

    // Galaxy parameters - facing the audience (flat on XY plane)
    const arms = 4; // 4 elegant spiral arms
    const galaxyRadius = 12;

    for (let i = 0; i < galaxyCount; i++) {
      const arm = Math.floor(Math.random() * arms);
      const armAngle = (arm / arms) * Math.PI * 2;

      // Distance from center with concentration towards center
      const distance = Math.pow(Math.random(), 0.5) * galaxyRadius;

      // Spiral tightness - more turns for aesthetic look
      const spiralAngle = distance * 0.7 + armAngle;

      // Spread increases with distance
      const spread = (Math.random() - 0.5) * (0.2 + distance * 0.12);

      // Galaxy lies flat on XY plane (facing audience/camera)
      galaxyPositions[i * 3] = Math.cos(spiralAngle) * distance + spread;     // X
      galaxyPositions[i * 3 + 1] = Math.sin(spiralAngle) * distance + spread; // Y
      galaxyPositions[i * 3 + 2] = (Math.random() - 0.5) * 0.3;               // Z (very thin)

      // Beautiful color gradient: golden core -> cyan/teal -> purple/magenta edges
      const colorMix = distance / galaxyRadius;
      let starColor;
      if (colorMix < 0.15) {
        // Bright golden/white core
        starColor = new THREE.Color(0xfffff0);
      } else if (colorMix < 0.35) {
        // Golden to cyan transition
        const t = (colorMix - 0.15) / 0.2;
        starColor = new THREE.Color().lerpColors(
          new THREE.Color(0xfff8dc),
          new THREE.Color(0x00ced1),
          t
        );
      } else if (colorMix < 0.6) {
        // Cyan to blue
        const t = (colorMix - 0.35) / 0.25;
        starColor = new THREE.Color().lerpColors(
          new THREE.Color(0x00ced1),
          new THREE.Color(0x4169e1),
          t
        );
      } else {
        // Blue to purple/magenta edges
        const t = (colorMix - 0.6) / 0.4;
        starColor = new THREE.Color().lerpColors(
          new THREE.Color(0x4169e1),
          new THREE.Color(0x9932cc),
          t
        );
      }

      galaxyColors[i * 3] = starColor.r;
      galaxyColors[i * 3 + 1] = starColor.g;
      galaxyColors[i * 3 + 2] = starColor.b;
    }

    galaxyGeometry.setAttribute('position', new THREE.BufferAttribute(galaxyPositions, 3));
    galaxyGeometry.setAttribute('color', new THREE.BufferAttribute(galaxyColors, 3));

    const galaxyMaterial = new THREE.PointsMaterial({
      size: 0.1,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    });

    const galaxy = new THREE.Points(galaxyGeometry, galaxyMaterial);
    // No X rotation - galaxy faces the audience directly
    galaxyGroup.add(galaxy);

    // Bright glowing galaxy core
    const coreGlowTexture = new THREE.CanvasTexture((() => {
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 256;
      const ctx = canvas.getContext('2d');

      // Multi-layered glow for depth
      const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
      gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
      gradient.addColorStop(0.1, 'rgba(255, 250, 230, 0.9)');
      gradient.addColorStop(0.25, 'rgba(255, 220, 180, 0.6)');
      gradient.addColorStop(0.5, 'rgba(100, 200, 255, 0.3)');
      gradient.addColorStop(0.75, 'rgba(150, 100, 255, 0.15)');
      gradient.addColorStop(1, 'rgba(100, 50, 200, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 256, 256);

      return canvas;
    })());

    const coreGlow = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: coreGlowTexture,
        transparent: true,
        blending: THREE.AdditiveBlending,
        opacity: 0.9,
      })
    );
    coreGlow.scale.set(5, 5, 1);
    galaxyGroup.add(coreGlow);
    stateRef.current.galaxyCore = coreGlow;

    alcoveGroup.add(galaxyGroup);
    stateRef.current.galaxy = galaxy;
    stateRef.current.galaxyGroup = galaxyGroup;

    // Rings and particles removed for cleaner look

    // ====== COSMIC PORTAL LIGHTING ======
    // Main spotlight with golden wisdom glow
    const mainSpot = new THREE.SpotLight(0xffd700, 5, 30, Math.PI / 5, 0.3, 1);
    mainSpot.position.set(0, 18, alcoveZ + 8);
    mainSpot.target.position.set(0, 6, alcoveZ + 5);
    mainSpot.castShadow = true;
    scene.add(mainSpot);
    scene.add(mainSpot.target);

    // Cosmic purple ambient glow behind bust
    const cosmicGlow = new THREE.PointLight(0x9370db, 3, 18);
    cosmicGlow.position.set(0, 10, alcoveZ - 1);
    scene.add(cosmicGlow);

    // Golden wisdom glow
    const wisdomGlow = new THREE.PointLight(0xffd700, 2.5, 15);
    wisdomGlow.position.set(0, 8, alcoveZ + 2);
    scene.add(wisdomGlow);

    // Side accent lights (cosmic teal)
    const leftAccent = new THREE.PointLight(0x00ced1, 1.5, 12);
    leftAccent.position.set(-6, 8, alcoveZ + 3);
    scene.add(leftAccent);

    const rightAccent = new THREE.PointLight(0xff69b4, 1.5, 12);
    rightAccent.position.set(6, 8, alcoveZ + 3);
    scene.add(rightAccent);

    // Deep space back light
    const spaceLight = new THREE.PointLight(0x4169e1, 2, 20);
    spaceLight.position.set(0, 12, alcoveZ - 3);
    scene.add(spaceLight);

    scene.add(alcoveGroup);
    stateRef.current.alcoveGroup = alcoveGroup;

    // Socrates Quotes - Elegant calligraphy directly on walls
    // POSITIONED TO AVOID OVERLAPPING WITH SUBJECTS AND PILLARS
    const quotesGroup = new THREE.Group();

    // Famous Socrates quotes - shorter versions for cleaner display
    const socratesQuotes = [
      'I know that I know nothing',
      'Wonder is the beginning of wisdom',
      'To find yourself, think for yourself',
      'Education is the kindling of a flame',
      'An honest man is always a child',
      'The unexamined life is not worth living',
    ];

    // Create wall quote function - positioned BETWEEN pillars for visibility
    const createWallQuote = (x, z, side, quoteIndex) => {
      const quote = socratesQuotes[quoteIndex % socratesQuotes.length];

      // LARGER Canvas for better visibility
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = 2048;
      canvas.height = 400;

      // Transparent background
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Decorative quote marks - large and elegant
      ctx.fillStyle = 'rgba(180, 150, 100, 0.4)';
      ctx.font = 'bold 180px Georgia, serif';
      ctx.fillText('"', 80, 180);
      ctx.fillText('"', 1850, 280);

      // Main quote text - MUCH LARGER and bolder
      ctx.fillStyle = '#1a1a1a';
      ctx.font = 'italic bold 88px "Times New Roman", Georgia, serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(quote, 1024, 200);

      // Decorative underline
      ctx.strokeStyle = 'rgba(180, 150, 100, 0.6)';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(400, 300);
      ctx.lineTo(1648, 300);
      ctx.stroke();

      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      const textMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(12, 3),  // MUCH LARGER plane
        new THREE.MeshBasicMaterial({ map: texture, transparent: true })
      );

      // Position HIGH on wall (y=12) and BETWEEN pillars
      textMesh.position.set(x, 12, z);
      textMesh.rotation.y = side === 'left' ? Math.PI / 2 : -Math.PI / 2;

      return textMesh;
    };

    // Calculate positions BETWEEN pillars (center of each gap) - NOT at pillar positions
    // Pillar positions: [22, 14, 6, -2, -10, -18]
    // Gap centers: (22+14)/2=18, (14+6)/2=10, (6+-2)/2=2, (-2+-10)/2=-6, (-10+-18)/2=-14
    const quotePositionsBetweenPillars = [];
    for (let i = 0; i < PILLAR_POSITIONS.length - 1; i++) {
      quotePositionsBetweenPillars.push((PILLAR_POSITIONS[i] + PILLAR_POSITIONS[i + 1]) / 2);
    }

    quotePositionsBetweenPillars.forEach((z, i) => {
      // Left wall quotes - high on wall, between pillars
      const leftQuote = createWallQuote(-HALL_WIDTH / 2 + 0.2, z, 'left', i);
      quotesGroup.add(leftQuote);

      // Right wall quotes - high on wall, between pillars
      const rightQuote = createWallQuote(HALL_WIDTH / 2 - 0.2, z, 'right', i);
      quotesGroup.add(rightQuote);
    });

    scene.add(quotesGroup);

    // Louvre-Style Barrel Vault Ceiling with Skylight
    const ceilingGroup = new THREE.Group();

    // Vault parameters - balanced proportions for museum aesthetics
    const pillarHeight = 10;  // Reduced pillar height
    const vaultRadius = HALL_WIDTH / 2;  // Half the hall width
    const vaultLength = HALL_DEPTH + 4;
    const skylightWidth = 4;
    const vaultBaseY = pillarHeight;  // Vault starts at pillar tops

    // Materials - realistic plaster/stone look
    const vaultMat = new THREE.MeshStandardMaterial({
      color: 0xf2ede5,
      roughness: 0.85,  // More matte for realistic ceiling
      metalness: 0.0,
      side: THREE.DoubleSide
    });

    const vaultTrimMat = new THREE.MeshStandardMaterial({
      color: 0xb8995a,  // More muted gold
      roughness: 0.55,  // Less shiny, more aged look
      metalness: 0.5
    });

    const skylightFrameMat = new THREE.MeshStandardMaterial({
      color: 0x2a2a2a,
      roughness: 0.4,
      metalness: 0.6
    });

    const glassMat = new THREE.MeshStandardMaterial({
      color: 0x99ccff,
      transparent: true,
      opacity: 0.5,
      emissive: 0x6699cc,
      emissiveIntensity: 0.3,
      side: THREE.DoubleSide
    });

    // Create barrel vault using half-cylinder
    // Slightly smaller radius to prevent wall clipping
    const actualVaultRadius = vaultRadius - 1;  // Proportional arch

    // Build the vault surface manually using BufferGeometry
    // This creates a half-pipe shape arching UPWARD over the hall
    const vaultSegmentsArc = 32;  // segments around the arc
    const vaultSegmentsLength = 1;  // segments along the hall

    const vaultVertices = [];
    const vaultIndices = [];
    const vaultNormals = [];
    const vaultUVs = [];

    // Generate vertices for a half-cylinder arching overhead
    for (let j = 0; j <= vaultSegmentsLength; j++) {
      const z = -vaultLength / 2 + (j / vaultSegmentsLength) * vaultLength;

      for (let i = 0; i <= vaultSegmentsArc; i++) {
        // Angle from 0 to PI - this creates an arch from +X, over +Y (up), to -X
        const angle = (i / vaultSegmentsArc) * Math.PI;

        // Position: x goes from +radius to -radius, y arches up
        const x = Math.cos(angle) * actualVaultRadius;
        const y = Math.sin(angle) * actualVaultRadius + vaultBaseY;

        vaultVertices.push(x, y, z);

        // Normal points inward (toward center of hall, downward)
        // For interior visibility, normals should point toward the viewer (down and in)
        vaultNormals.push(-Math.cos(angle), -Math.sin(angle), 0);

        // UVs
        vaultUVs.push(i / vaultSegmentsArc, j / vaultSegmentsLength);
      }
    }

    // Generate indices for triangles
    for (let j = 0; j < vaultSegmentsLength; j++) {
      for (let i = 0; i < vaultSegmentsArc; i++) {
        const a = j * (vaultSegmentsArc + 1) + i;
        const b = a + 1;
        const c = a + (vaultSegmentsArc + 1);
        const d = c + 1;

        // Two triangles per quad
        vaultIndices.push(a, b, c);
        vaultIndices.push(b, d, c);
      }
    }

    const vaultBufferGeo = new THREE.BufferGeometry();
    vaultBufferGeo.setAttribute('position', new THREE.Float32BufferAttribute(vaultVertices, 3));
    vaultBufferGeo.setAttribute('normal', new THREE.Float32BufferAttribute(vaultNormals, 3));
    vaultBufferGeo.setAttribute('uv', new THREE.Float32BufferAttribute(vaultUVs, 2));
    vaultBufferGeo.setIndex(vaultIndices);

    const fullVault = new THREE.Mesh(vaultBufferGeo, vaultMat);
    ceilingGroup.add(fullVault);

    // Skylight at the apex (top of the arch)
    const skylightY = vaultBaseY + actualVaultRadius;

    // Glass skylight panel
    const skylightGlass = new THREE.Mesh(
      new THREE.PlaneGeometry(skylightWidth, vaultLength - 4),
      glassMat
    );
    skylightGlass.rotation.x = -Math.PI / 2;
    skylightGlass.position.set(0, skylightY - 0.1, 0);
    ceilingGroup.add(skylightGlass);

    // Skylight frame bars
    const leftFrameBar = new THREE.Mesh(
      new THREE.BoxGeometry(0.15, 0.3, vaultLength - 2),
      skylightFrameMat
    );
    leftFrameBar.position.set(-skylightWidth / 2, skylightY - 0.15, 0);
    ceilingGroup.add(leftFrameBar);

    const rightFrameBar = leftFrameBar.clone();
    rightFrameBar.position.x = skylightWidth / 2;
    ceilingGroup.add(rightFrameBar);

    const centerFrameBar = new THREE.Mesh(
      new THREE.BoxGeometry(0.08, 0.2, vaultLength - 2),
      skylightFrameMat
    );
    centerFrameBar.position.set(0, skylightY - 0.1, 0);
    ceilingGroup.add(centerFrameBar);

    // Cross bars on skylight
    const crossSpacing = 6;
    const numCross = Math.floor(vaultLength / crossSpacing);
    for (let i = 0; i <= numCross; i++) {
      const crossBar = new THREE.Mesh(
        new THREE.BoxGeometry(skylightWidth + 0.3, 0.2, 0.1),
        skylightFrameMat
      );
      crossBar.position.set(0, skylightY - 0.1, -vaultLength / 2 + 2 + i * crossSpacing);
      ceilingGroup.add(crossBar);
    }

    // Decorative arch ribs - UPWARD curving (angles 0 to PI)
    const ribSpacing = 7;
    const numRibs = Math.floor(vaultLength / ribSpacing);

    for (let i = 0; i <= numRibs; i++) {
      const z = -vaultLength / 2 + 3 + i * ribSpacing;

      // Create arch points going from right wall, up over top, to left wall
      // angle 0 = right side, angle PI/2 = top, angle PI = left side
      const archPoints = [];
      for (let a = 0; a <= Math.PI; a += Math.PI / 20) {
        const x = Math.cos(a) * (actualVaultRadius - 0.05);
        const y = Math.sin(a) * (actualVaultRadius - 0.05) + vaultBaseY;
        archPoints.push(new THREE.Vector3(x, y, z));
      }

      // Create tube along the arch path
      const archCurve = new THREE.CatmullRomCurve3(archPoints);
      const archGeo = new THREE.TubeGeometry(archCurve, 24, 0.06, 8, false);
      const archRib = new THREE.Mesh(archGeo, vaultTrimMat);
      ceilingGroup.add(archRib);
    }

    // Crown molding where vault meets walls
    const crownMat = new THREE.MeshStandardMaterial({
      color: 0xf0ebe0,
      roughness: 0.4
    });

    const leftCrown = new THREE.Mesh(
      new THREE.BoxGeometry(1.0, 0.6, HALL_DEPTH + 2),
      crownMat
    );
    leftCrown.position.set(-HALL_WIDTH / 2 + 0.5, vaultBaseY - 0.3, 0);
    ceilingGroup.add(leftCrown);

    const rightCrown = leftCrown.clone();
    rightCrown.position.x = HALL_WIDTH / 2 - 0.5;
    ceilingGroup.add(rightCrown);

    // Gold trim on crown
    const goldTrim = new THREE.Mesh(
      new THREE.BoxGeometry(0.12, 0.2, HALL_DEPTH + 2),
      vaultTrimMat
    );
    goldTrim.position.set(-HALL_WIDTH / 2 + 1.0, vaultBaseY - 0.1, 0);
    ceilingGroup.add(goldTrim);

    const rightGoldTrim = goldTrim.clone();
    rightGoldTrim.position.x = HALL_WIDTH / 2 - 1.0;
    ceilingGroup.add(rightGoldTrim);

    // Skylight illumination
    for (let i = 0; i < 5; i++) {
      const light = new THREE.PointLight(0xffffff, 0.6, 25);
      light.position.set(0, skylightY - 3, -vaultLength / 2 + 10 + i * 15);
      ceilingGroup.add(light);
    }

    galleryGroup.add(ceilingGroup);

    scene.add(galleryGroup);

    // Add baseboards along walls for realism
    const baseboardMat = new THREE.MeshStandardMaterial({
      color: 0xe8e4dc,
      roughness: 0.4
    });

    // Left baseboard
    const leftBaseboard = new THREE.Mesh(
      new THREE.BoxGeometry(0.15, 0.4, HALL_DEPTH - 4),
      baseboardMat
    );
    leftBaseboard.position.set(-HALL_WIDTH / 2 + 0.08, 0.2, 0);
    scene.add(leftBaseboard);

    // Right baseboard
    const rightBaseboard = new THREE.Mesh(
      new THREE.BoxGeometry(0.15, 0.4, HALL_DEPTH - 4),
      baseboardMat
    );
    rightBaseboard.position.set(HALL_WIDTH / 2 - 0.08, 0.2, 0);
    scene.add(rightBaseboard);

    // 4. Load the character model
    const playerGroup = new THREE.Group();
    playerGroup.position.set(0, 0, 10);
    playerGroup.rotation.y = Math.PI; // Face towards Socrates (away from user)
    scene.add(playerGroup);
    stateRef.current.player = playerGroup;

    const loader = new FBXLoader();

    console.log('Loading Mixamo character with animation...');
    setLoadingStatus('Loading character model...');

    // Load the Mixamo animated model (character + animation included)
    loader.load(
      '/models/assassin/assassin_walking.fbx',
      (model) => {
        console.log('Mixamo model loaded!');
        console.log('Animations:', model.animations.length);
        setLoadingStages(prev => ({ ...prev, characterModel: true }));
        setLoadingStatus('Character loaded');

        // Calculate bounding box for proper scale
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());

        // Scale to roughly 2 units tall
        const targetHeight = 2;
        const scaleFactor = targetHeight / size.y;
        model.scale.setScalar(scaleFactor);

        // Place feet on ground
        const scaledMinY = box.min.y * scaleFactor;
        model.position.y = -scaledMinY;
        stateRef.current.baseY = model.position.y;

        // Keep embedded Mixamo materials (which have colors) - just enable shadows
        model.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            // Don't override materials - keep Mixamo's embedded textures/colors
            console.log('Mesh:', child.name, 'Material:', child.material?.name || 'unnamed');
          }
        });

        playerGroup.add(model);
        stateRef.current.fbxModel = model;

        // Setup smooth looping animation
        if (model.animations && model.animations.length > 0) {
          console.log('Setting up animation:', model.animations[0].name);
          const mixer = new THREE.AnimationMixer(model);
          stateRef.current.mixer = mixer;

          const clip = model.animations[0];
          console.log('Animation duration:', clip.duration, 'seconds');

          const walkAction = mixer.clipAction(clip);

          // Configure for smooth continuous loop
          walkAction.setLoop(THREE.LoopRepeat, Infinity);
          walkAction.clampWhenFinished = false;

          // Use timeScale for smooth control (0 = paused, 1 = playing)
          walkAction.timeScale = 0;
          walkAction.play();

          stateRef.current.walkAction = walkAction;
          stateRef.current.isWalking = false;
        }

        setModelStatus('loaded');
        console.log('Character ready!');
      },
      (progress) => {
        if (progress.total > 0) {
          const percent = Math.round((progress.loaded / progress.total) * 100);
          console.log(`Loading FBX: ${percent}%`);
        }
      },
      (error) => {
        console.error('FBX load error:', error);
        setModelStatus('error');
        // Still mark as loaded to not block the app
        setLoadingStages(prev => ({ ...prev, characterModel: true }));
        setLoadingStatus('Character load failed - continuing...');
      }
    );

    // 5. Subject Portals - Elegant gallery-style frames matching the museum theme
    // Subject-specific illustration data for artistic representations
    const subjectIllustrations = {
      physics: { symbol: '⚛️', shapes: ['circle', 'orbit', 'wave'], accent: '#3B82F6' },
      chemistry: { symbol: '🧪', shapes: ['hexagon', 'bond', 'bubble'], accent: '#10B981' },
      biology: { symbol: '🧬', shapes: ['helix', 'cell', 'leaf'], accent: '#EC4899' },
      mathematics: { symbol: '∑', shapes: ['triangle', 'circle', 'grid'], accent: '#8B5CF6' },
      computer_science: { symbol: '</>',  shapes: ['bracket', 'binary', 'circuit'], accent: '#06B6D4' },
      english: { symbol: '✒️', shapes: ['quill', 'book', 'scroll'], accent: '#F59E0B' },
      history: { symbol: '🏛️', shapes: ['column', 'arch', 'scroll'], accent: '#78716C' },
      philosophy: { symbol: '∞', shapes: ['infinity', 'eye', 'tree'], accent: '#6366F1' },
      psychology: { symbol: '🧠', shapes: ['brain', 'wave', 'mirror'], accent: '#F472B6' },
      economics: { symbol: '📊', shapes: ['chart', 'coin', 'arrow'], accent: '#22C55E' },
    };

    // Helper function to draw artistic illustrations on canvas
    // Using thick lines and solid shapes to avoid aliasing artifacts
    const drawSubjectArt = (ctx, subject, width, height) => {
      const illustration = subjectIllustrations[subject.id] || { symbol: subject.icon, shapes: [], accent: subject.color };
      const centerX = width / 2;
      const centerY = height * 0.38;

      // Draw artistic background elements based on subject
      ctx.save();
      ctx.globalAlpha = 0.15;

      if (subject.id === 'physics') {
        // Atomic orbits - thick lines
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 8;
        for (let i = 0; i < 3; i++) {
          ctx.beginPath();
          ctx.ellipse(centerX, centerY, 140 + i * 30, 60 + i * 15, (i * Math.PI) / 3, 0, Math.PI * 2);
          ctx.stroke();
        }
        // Nucleus - solid circle
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = illustration.accent;
        ctx.beginPath();
        ctx.arc(centerX, centerY, 35, 0, Math.PI * 2);
        ctx.fill();
      } else if (subject.id === 'chemistry') {
        // Hexagonal molecular structure - thick strokes
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 8;
        const hexRadius = 55;
        const positions = [[0, 0], [-85, -55], [85, -55], [-85, 55], [85, 55]];
        positions.forEach(([ox, oy]) => {
          ctx.beginPath();
          for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 6;
            const x = centerX + ox + Math.cos(angle) * hexRadius;
            const y = centerY + oy + Math.sin(angle) * hexRadius;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.closePath();
          ctx.stroke();
        });
      } else if (subject.id === 'biology') {
        // DNA helix - thick strands
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 10;
        for (let i = 0; i < 2; i++) {
          ctx.beginPath();
          for (let t = -150; t <= 150; t += 8) {
            const x = centerX + Math.sin((t / 30) + i * Math.PI) * 90;
            const y = centerY + t;
            if (t === -150) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.stroke();
        }
        // Cross bars - thick
        ctx.lineWidth = 6;
        for (let t = -120; t <= 120; t += 50) {
          const x1 = centerX + Math.sin(t / 30) * 90;
          const x2 = centerX + Math.sin(t / 30 + Math.PI) * 90;
          ctx.beginPath();
          ctx.moveTo(x1, centerY + t);
          ctx.lineTo(x2, centerY + t);
          ctx.stroke();
        }
      } else if (subject.id === 'mathematics') {
        // Geometric shapes - thick strokes
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 8;
        // Triangle
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - 100);
        ctx.lineTo(centerX - 90, centerY + 60);
        ctx.lineTo(centerX + 90, centerY + 60);
        ctx.closePath();
        ctx.stroke();
        // Circle
        ctx.beginPath();
        ctx.arc(centerX, centerY, 70, 0, Math.PI * 2);
        ctx.stroke();
        // Pi symbol watermark - large and visible
        ctx.globalAlpha = 0.1;
        ctx.font = 'bold 220px Georgia';
        ctx.fillStyle = illustration.accent;
        ctx.textAlign = 'center';
        ctx.fillText('π', centerX, centerY + 80);
      } else if (subject.id === 'computer_science') {
        // Code brackets - large and bold
        ctx.globalAlpha = 0.2;
        ctx.font = 'bold 200px monospace';
        ctx.fillStyle = illustration.accent;
        ctx.textAlign = 'center';
        ctx.fillText('<', centerX - 90, centerY + 50);
        ctx.fillText('/>', centerX + 70, centerY + 50);
        // Simple binary - larger text
        ctx.font = 'bold 32px monospace';
        ctx.globalAlpha = 0.12;
        for (let row = 0; row < 5; row++) {
          for (let col = 0; col < 8; col++) {
            const char = Math.random() > 0.5 ? '1' : '0';
            ctx.fillText(char, centerX - 120 + col * 32, centerY - 120 + row * 45);
          }
        }
      } else if (subject.id === 'english') {
        // Text lines as solid rectangles
        ctx.fillStyle = illustration.accent;
        for (let i = 0; i < 5; i++) {
          const lineWidth = 200 - i * 25;
          ctx.fillRect(centerX - lineWidth / 2, centerY - 70 + i * 45, lineWidth, 8);
        }
        // Quill feather shape - larger
        ctx.globalAlpha = 0.2;
        ctx.beginPath();
        ctx.ellipse(centerX + 110, centerY - 90, 70, 20, Math.PI / 4, 0, Math.PI * 2);
        ctx.fill();
      } else if (subject.id === 'history') {
        // Greek columns - filled rectangles
        ctx.fillStyle = illustration.accent;
        const colPositions = [-90, 0, 90];
        colPositions.forEach(ox => {
          // Column shaft - solid fill
          ctx.fillRect(centerX + ox - 18, centerY - 80, 36, 170);
          // Capital - wider
          ctx.fillRect(centerX + ox - 30, centerY - 100, 60, 20);
          // Base
          ctx.fillRect(centerX + ox - 25, centerY + 90, 50, 15);
        });
        // Pediment - thick stroke
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 10;
        ctx.beginPath();
        ctx.moveTo(centerX - 130, centerY - 100);
        ctx.lineTo(centerX, centerY - 150);
        ctx.lineTo(centerX + 130, centerY - 100);
        ctx.closePath();
        ctx.stroke();
      } else if (subject.id === 'philosophy') {
        // Infinity symbol - thick
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 10;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.bezierCurveTo(centerX + 90, centerY - 70, centerX + 130, centerY + 70, centerX, centerY);
        ctx.bezierCurveTo(centerX - 90, centerY - 70, centerX - 130, centerY + 70, centerX, centerY);
        ctx.stroke();
        // Eye of wisdom - larger
        ctx.globalAlpha = 0.18;
        ctx.lineWidth = 8;
        ctx.beginPath();
        ctx.ellipse(centerX, centerY - 90, 60, 30, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(centerX, centerY - 90, 18, 0, Math.PI * 2);
        ctx.fill();
      } else if (subject.id === 'psychology') {
        // Brain waves - thick strokes
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 8;
        for (let wave = 0; wave < 4; wave++) {
          ctx.beginPath();
          for (let x = -150; x <= 150; x += 10) {
            const y = centerY - 70 + wave * 55 + Math.sin(x / 25 + wave) * 20;
            if (x === -150) ctx.moveTo(centerX + x, y);
            else ctx.lineTo(centerX + x, y);
          }
          ctx.stroke();
        }
        // Brain outline - larger ellipse
        ctx.globalAlpha = 0.12;
        ctx.lineWidth = 10;
        ctx.beginPath();
        ctx.ellipse(centerX, centerY, 110, 90, 0, 0, Math.PI * 2);
        ctx.stroke();
      } else if (subject.id === 'economics') {
        // Chart bars - solid rectangles
        ctx.fillStyle = illustration.accent;
        ctx.globalAlpha = 0.25;
        const barHeights = [70, 100, 80, 120, 95, 140];
        barHeights.forEach((h, i) => {
          ctx.fillRect(centerX - 140 + i * 50, centerY + 90 - h, 35, h);
        });
        // Trend line - thick
        ctx.strokeStyle = illustration.accent;
        ctx.lineWidth = 10;
        ctx.globalAlpha = 0.3;
        ctx.beginPath();
        ctx.moveTo(centerX - 140, centerY + 50);
        ctx.lineTo(centerX + 110, centerY - 90);
        ctx.stroke();
        // Arrow head - filled triangle
        ctx.fillStyle = illustration.accent;
        ctx.beginPath();
        ctx.moveTo(centerX + 110, centerY - 90);
        ctx.lineTo(centerX + 80, centerY - 70);
        ctx.lineTo(centerX + 90, centerY - 55);
        ctx.closePath();
        ctx.fill();
      }

      ctx.restore();
    };

    const subjectPortals = SUBJECT_CHANNELS.map(subject => {
      const g = new THREE.Group();

      // Outer frame - elegant dark wood/olive matching gallery theme
      const frameMat = new THREE.MeshStandardMaterial({
        color: 0x2a3020,
        roughness: 0.6,
        metalness: 0.1
      });

      // Main frame - LARGER size for better visibility
      const frame = new THREE.Mesh(
        new THREE.BoxGeometry(5.2, 3.8, 0.25),
        frameMat
      );
      frame.castShadow = true;

      // Inner frame detail - aged gold trim
      const innerFrame = new THREE.Mesh(
        new THREE.BoxGeometry(5.0, 3.6, 0.06),
        new THREE.MeshStandardMaterial({
          color: 0xa89050,  // More muted gold
          roughness: 0.55,  // Less shiny
          metalness: 0.35   // Less metallic
        })
      );
      innerFrame.position.z = 0.10;

      // Canvas with subject image - use BasicMaterial to avoid lighting artifacts
      const canvasMat = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        side: THREE.FrontSide
      });
      const canvas = new THREE.Mesh(
        new THREE.PlaneGeometry(4.6, 3.2),
        canvasMat
      );
      canvas.position.z = 0.16;  // Move further forward to prevent z-fighting

      // Load actual subject image using TextureLoader
      const textureLoader = new THREE.TextureLoader();
      const subjectImagePath = SUBJECT_IMAGES[subject.id];

      if (subjectImagePath) {
        const imageTexture = textureLoader.load(subjectImagePath, (texture) => {
          // Texture loaded successfully - configure it
          texture.colorSpace = THREE.SRGBColorSpace;
          texture.generateMipmaps = false;
          texture.minFilter = THREE.LinearFilter;
          texture.magFilter = THREE.LinearFilter;
          canvas.material.map = texture;
          canvas.material.needsUpdate = true;
        });
      }

      // Create name label overlay at the bottom
      const labelCanvas = document.createElement('canvas');
      labelCanvas.width = 512;
      labelCanvas.height = 80;
      const ctx = labelCanvas.getContext('2d');
      const accentColor = subject.color;

      // Semi-transparent dark background for label
      ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
      ctx.fillRect(0, 0, 512, 80);

      // Subject name - elegant typography
      ctx.fillStyle = '#ffffff';
      ctx.font = '600 28px Georgia, serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(subject.name, 256, 30);

      // Accent underline
      ctx.fillStyle = accentColor;
      ctx.fillRect(180, 50, 152, 3);

      // Description - refined
      ctx.fillStyle = '#cccccc';
      ctx.font = '14px Georgia, serif';
      const shortDesc = subject.description.length > 45
        ? subject.description.substring(0, 42) + '...'
        : subject.description;
      ctx.fillText(shortDesc, 256, 68);

      // Create label texture
      const labelTexture = new THREE.CanvasTexture(labelCanvas);
      labelTexture.colorSpace = THREE.SRGBColorSpace;
      labelTexture.generateMipmaps = false;
      labelTexture.minFilter = THREE.LinearFilter;
      labelTexture.magFilter = THREE.LinearFilter;

      // Create label mesh positioned at bottom of canvas
      const labelMat = new THREE.MeshBasicMaterial({
        map: labelTexture,
        transparent: true,
        side: THREE.FrontSide
      });
      const labelMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(4.6, 0.65),
        labelMat
      );
      labelMesh.position.z = 0.17;
      labelMesh.position.y = -1.3;  // Position at bottom of larger canvas

      // Solid backing to prevent wall texture from showing through
      const backingMat = new THREE.MeshBasicMaterial({
        color: 0x1a1a1a,  // Dark backing
        side: THREE.BackSide
      });
      const backing = new THREE.Mesh(
        new THREE.PlaneGeometry(5.0, 3.6),
        backingMat
      );
      backing.position.z = -0.03;

      // Lighting
      const frameLight = new THREE.SpotLight(0xfff8e0, 0.4, 6, Math.PI / 6, 0.5);
      frameLight.position.set(0, 2, 1.5);
      frameLight.target = canvas;

      const glowLight = new THREE.PointLight(0xfff5e6, 0.15, 5);
      glowLight.position.set(0, 0, 1);

      g.add(backing, frame, innerFrame, canvas, labelMesh, frameLight, frameLight.target, glowLight);

      // Position frames slightly away from walls to prevent z-fighting
      const x = subject.side === 'left' ? -HALL_WIDTH / 2 + 0.3 : HALL_WIDTH / 2 - 0.3;
      g.position.set(x, 5, subject.z);
      g.rotation.y = subject.side === 'left' ? Math.PI / 2 : -Math.PI / 2;

      g.userData.glowLight = glowLight;
      g.userData.baseGlowIntensity = 0.15;

      scene.add(g);
      return { group: g, data: subject };
    });

    // Store as paintings for compatibility
    const paintings = subjectPortals;

    // 5. Classical Pillars - Museum-style columns between subjects
    // HIGH QUALITY with more geometry segments
    const createClassicalPillar = (x, z, side) => {
      const pillarGroup = new THREE.Group();

      // Pillar dimensions - realistic museum proportions
      const pillarHeight = 10;
      const shaftRadius = 0.35;  // Slightly thicker for better proportions
      const baseHeight = 0.5;
      const capitalHeight = 0.6;

      // Material for marble effect - realistic stone texture
      const marbleMat = new THREE.MeshStandardMaterial({
        color: 0xf0ebe3,
        roughness: 0.7,
        metalness: 0.0
      });

      // Darker marble for accent details
      const darkMarbleMat = new THREE.MeshStandardMaterial({
        color: 0xe0d8c8,
        roughness: 0.75,
        metalness: 0.0
      });

      // Base - multi-tiered plinth
      const base1 = new THREE.Mesh(
        new THREE.BoxGeometry(1.4, 0.2, 1.4),
        darkMarbleMat
      );
      base1.position.y = 0.1;
      base1.castShadow = true;
      base1.receiveShadow = true;

      const base2 = new THREE.Mesh(
        new THREE.BoxGeometry(1.2, 0.2, 1.2),
        marbleMat
      );
      base2.position.y = 0.3;
      base2.castShadow = true;

      // HIGH QUALITY: 48 segments for smooth curves
      const base3 = new THREE.Mesh(
        new THREE.CylinderGeometry(shaftRadius + 0.15, shaftRadius + 0.2, 0.2, 48),
        darkMarbleMat
      );
      base3.position.y = 0.5;
      base3.castShadow = true;

      // Main shaft - HIGH QUALITY: 48 radial segments, 8 height segments
      const shaftGeo = new THREE.CylinderGeometry(shaftRadius, shaftRadius + 0.05, pillarHeight - baseHeight - capitalHeight, 48, 8);
      const shaft = new THREE.Mesh(shaftGeo, marbleMat);
      shaft.position.y = baseHeight + (pillarHeight - baseHeight - capitalHeight) / 2;
      shaft.castShadow = true;
      shaft.receiveShadow = true;

      // Fluting grooves (decorative vertical lines) - 16 flutes for elegance
      const fluteCount = 16;
      for (let i = 0; i < fluteCount; i++) {
        const angle = (i / fluteCount) * Math.PI * 2;
        const fluteGeo = new THREE.BoxGeometry(0.06, pillarHeight - baseHeight - capitalHeight - 0.5, 0.12);
        const flute = new THREE.Mesh(fluteGeo, darkMarbleMat);
        flute.position.x = Math.cos(angle) * (shaftRadius + 0.02);
        flute.position.z = Math.sin(angle) * (shaftRadius + 0.02);
        flute.position.y = shaft.position.y;
        flute.rotation.y = -angle;
        pillarGroup.add(flute);
      }

      // Capital - Doric style with echinus and abacus - HIGH QUALITY
      const echinus = new THREE.Mesh(
        new THREE.CylinderGeometry(shaftRadius + 0.25, shaftRadius, 0.3, 48),
        marbleMat
      );
      echinus.position.y = pillarHeight - capitalHeight + 0.15;
      echinus.castShadow = true;

      const abacus = new THREE.Mesh(
        new THREE.BoxGeometry(1.3, 0.25, 1.3),
        darkMarbleMat
      );
      abacus.position.y = pillarHeight - capitalHeight / 2 + 0.2;
      abacus.castShadow = true;

      // Decorative ring at top of shaft - HIGH QUALITY: 48 segments
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(shaftRadius + 0.08, 0.04, 16, 48),
        darkMarbleMat
      );
      ring.position.y = pillarHeight - capitalHeight - 0.1;
      ring.rotation.x = Math.PI / 2;

      // Add all parts to group
      pillarGroup.add(base1, base2, base3, shaft, echinus, abacus, ring);

      // Position the pillar
      const wallOffset = 0.6; // Distance from wall
      const pillarX = side === 'left' ? -HALL_WIDTH / 2 + wallOffset : HALL_WIDTH / 2 - wallOffset;
      pillarGroup.position.set(pillarX, 0, z);

      // Add subtle lighting on each pillar
      const pillarLight = new THREE.PointLight(0xfff8e0, 0.1, 6);
      pillarLight.position.set(0, pillarHeight - 2, 1);
      pillarGroup.add(pillarLight);

      scene.add(pillarGroup);
      return pillarGroup;
    };

    // Place 6 pillars per wall to create 5 gaps with 2 subjects each
    // Using PILLAR_POSITIONS constant defined at top
    PILLAR_POSITIONS.forEach(z => {
      createClassicalPillar(0, z, 'left');
      createClassicalPillar(0, z, 'right');
    });

    // 5-LIGHTING. Wall Sconces and Chandeliers - Elegant Museum Lighting
    const createWallSconce = (x, z, side) => {
      const sconceGroup = new THREE.Group();

      // Sconce materials - aged brass look
      const brassMat = new THREE.MeshStandardMaterial({
        color: 0xb59555,  // More muted brass
        roughness: 0.5,   // More worn/aged
        metalness: 0.45
      });

      const glassMat = new THREE.MeshStandardMaterial({
        color: 0xfffef8,
        roughness: 0.1,
        metalness: 0.1,
        transparent: true,
        opacity: 0.6
      });

      // Wall plate (decorative backplate)
      const backplate = new THREE.Mesh(
        new THREE.BoxGeometry(0.4, 0.6, 0.08),
        brassMat
      );
      sconceGroup.add(backplate);

      // Decorative frame on backplate
      const frameRing = new THREE.Mesh(
        new THREE.TorusGeometry(0.18, 0.025, 8, 16),
        brassMat
      );
      frameRing.position.z = 0.04;
      sconceGroup.add(frameRing);

      // Arm extending from wall
      const arm = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.03, 0.35, 8),
        brassMat
      );
      arm.rotation.x = Math.PI / 2;
      arm.position.set(0, 0, 0.22);
      sconceGroup.add(arm);

      // Decorative curl at end
      const curl = new THREE.Mesh(
        new THREE.TorusGeometry(0.06, 0.02, 8, 12, Math.PI),
        brassMat
      );
      curl.rotation.x = Math.PI / 2;
      curl.rotation.z = Math.PI / 2;
      curl.position.set(0, -0.06, 0.38);
      sconceGroup.add(curl);

      // Candle holder cup
      const cup = new THREE.Mesh(
        new THREE.CylinderGeometry(0.06, 0.04, 0.05, 12),
        brassMat
      );
      cup.position.set(0, 0.02, 0.4);
      sconceGroup.add(cup);

      // Glass shade (frosted tulip shape)
      const shadeGeo = new THREE.CylinderGeometry(0.12, 0.06, 0.2, 12, 1, true);
      const shade = new THREE.Mesh(shadeGeo, glassMat);
      shade.position.set(0, 0.15, 0.4);
      sconceGroup.add(shade);

      // Light source inside shade
      const sconceLight = new THREE.PointLight(0xffedd5, 0.4, 8);
      sconceLight.position.set(0, 0.12, 0.4);
      sconceLight.castShadow = true;
      sconceGroup.add(sconceLight);

      // Warm glow effect
      const glowLight = new THREE.PointLight(0xffa64d, 0.15, 3);
      glowLight.position.set(0, 0.1, 0.4);
      sconceGroup.add(glowLight);

      // Position the sconce on wall
      const wallOffset = 0.08;
      const sconceX = side === 'left' ? -HALL_WIDTH / 2 + wallOffset : HALL_WIDTH / 2 - wallOffset;
      sconceGroup.position.set(sconceX, 8, z);
      sconceGroup.rotation.y = side === 'left' ? Math.PI / 2 : -Math.PI / 2;

      scene.add(sconceGroup);
      return sconceGroup;
    };

    // Place sconces at pillar positions
    PILLAR_POSITIONS.forEach(z => {
      createWallSconce(0, z, 'left');
      createWallSconce(0, z, 'right');
    });

    // ====== VISIBLE SPOTLIGHTS FOCUSED ON EACH SUBJECT ======
    // Create museum-style ceiling spotlights that illuminate each subject frame
    const createSubjectSpotlight = (subject) => {
      const spotGroup = new THREE.Group();
      const subjectX = subject.side === 'left' ? -HALL_WIDTH / 2 + 1 : HALL_WIDTH / 2 - 1;
      const subjectZ = subject.z;

      // Visible spotlight fixture on ceiling
      const fixtureMat = new THREE.MeshStandardMaterial({
        color: 0x2a2a2a,
        roughness: 0.3,
        metalness: 0.8
      });

      // Track rail segment
      const trackGeo = new THREE.BoxGeometry(0.15, 0.08, 1.2);
      const track = new THREE.Mesh(trackGeo, fixtureMat);
      track.position.set(subjectX * 0.7, HALL_HEIGHT - 0.5, subjectZ);
      spotGroup.add(track);

      // Spotlight housing (cylindrical)
      const housingGeo = new THREE.CylinderGeometry(0.12, 0.15, 0.35, 16);
      const housing = new THREE.Mesh(housingGeo, fixtureMat);
      housing.position.set(subjectX * 0.7, HALL_HEIGHT - 0.75, subjectZ);
      // Angle towards subject
      housing.rotation.z = subject.side === 'left' ? -0.4 : 0.4;
      spotGroup.add(housing);

      // Glowing lens/bulb
      const lensMat = new THREE.MeshBasicMaterial({
        color: 0xffffee,
        transparent: true,
        opacity: 0.9
      });
      const lensGeo = new THREE.CircleGeometry(0.1, 16);
      const lens = new THREE.Mesh(lensGeo, lensMat);
      lens.position.set(
        subjectX * 0.7 + (subject.side === 'left' ? -0.12 : 0.12),
        HALL_HEIGHT - 0.9,
        subjectZ
      );
      lens.rotation.y = subject.side === 'left' ? -Math.PI / 2 : Math.PI / 2;
      lens.rotation.z = subject.side === 'left' ? -0.4 : 0.4;
      spotGroup.add(lens);

      // Visible light cone (volumetric effect)
      const coneHeight = 8;
      const coneGeo = new THREE.ConeGeometry(2, coneHeight, 32, 1, true);
      const coneMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(subject.color).multiplyScalar(0.3),
        transparent: true,
        opacity: 0.08,
        side: THREE.DoubleSide,
        depthWrite: false
      });
      const cone = new THREE.Mesh(coneGeo, coneMat);
      cone.position.set(subjectX, HALL_HEIGHT - 4.5, subjectZ);
      cone.rotation.z = subject.side === 'left' ? 0.3 : -0.3;
      spotGroup.add(cone);

      // Actual spotlight for illumination
      const spotlight = new THREE.SpotLight(
        new THREE.Color(subject.color).lerp(new THREE.Color(0xffffff), 0.7),
        2.5,
        15,
        Math.PI / 8,
        0.5,
        1
      );
      spotlight.position.set(subjectX * 0.6, HALL_HEIGHT - 1, subjectZ);
      spotlight.target.position.set(subjectX, 5, subjectZ);
      spotGroup.add(spotlight);
      spotGroup.add(spotlight.target);

      scene.add(spotGroup);
      return spotGroup;
    };

    // Create spotlights for all subjects
    SUBJECT_CHANNELS.forEach(subject => {
      createSubjectSpotlight(subject);
    });

    // Create elegant chandeliers
    const createChandelier = (x, z) => {
      const chandelierGroup = new THREE.Group();

      const brassMat = new THREE.MeshStandardMaterial({
        color: 0xb59555,  // Aged brass
        roughness: 0.5,
        metalness: 0.45
      });

      const crystalMat = new THREE.MeshStandardMaterial({
        color: 0xf8f8f8,
        roughness: 0.15,  // Slightly more matte
        metalness: 0.1,
        transparent: true,
        opacity: 0.65
      });

      // Central stem
      const stem = new THREE.Mesh(
        new THREE.CylinderGeometry(0.08, 0.08, 1.5, 12),
        brassMat
      );
      stem.position.y = 0.75;
      chandelierGroup.add(stem);

      // Top canopy
      const canopy = new THREE.Mesh(
        new THREE.ConeGeometry(0.3, 0.2, 12),
        brassMat
      );
      canopy.position.y = 1.5;
      chandelierGroup.add(canopy);

      // Central decorative ball
      const centerBall = new THREE.Mesh(
        new THREE.SphereGeometry(0.15, 16, 16),
        brassMat
      );
      centerBall.position.y = 0;
      chandelierGroup.add(centerBall);

      // Bottom finial
      const finial = new THREE.Mesh(
        new THREE.ConeGeometry(0.08, 0.25, 8),
        brassMat
      );
      finial.position.y = -0.35;
      finial.rotation.x = Math.PI;
      chandelierGroup.add(finial);

      // Arms with lights (6 arms in a circle)
      const armCount = 6;
      for (let i = 0; i < armCount; i++) {
        const angle = (i / armCount) * Math.PI * 2;
        const armGroup = new THREE.Group();

        // Curved arm
        const armLength = 0.8;
        const arm = new THREE.Mesh(
          new THREE.CylinderGeometry(0.025, 0.025, armLength, 8),
          brassMat
        );
        arm.rotation.z = Math.PI / 3;
        arm.position.set(armLength / 2 * Math.cos(Math.PI / 6), armLength / 2 * Math.sin(Math.PI / 6), 0);
        armGroup.add(arm);

        // Candle cup at end
        const cup = new THREE.Mesh(
          new THREE.CylinderGeometry(0.06, 0.04, 0.06, 10),
          brassMat
        );
        cup.position.set(armLength * 0.85, armLength * 0.5, 0);
        armGroup.add(cup);

        // Crystal drop
        const crystal = new THREE.Mesh(
          new THREE.OctahedronGeometry(0.05),
          crystalMat
        );
        crystal.position.set(armLength * 0.85, armLength * 0.35, 0);
        crystal.scale.y = 1.8;
        armGroup.add(crystal);

        // Light for this arm
        const armLight = new THREE.PointLight(0xffeedd, 0.25, 6);
        armLight.position.set(armLength * 0.85, armLength * 0.55, 0);
        armGroup.add(armLight);

        armGroup.rotation.y = angle;
        armGroup.position.y = 0;
        chandelierGroup.add(armGroup);
      }

      // Central main light
      const mainLight = new THREE.PointLight(0xfff5e0, 0.6, 12);
      mainLight.position.y = 0;
      mainLight.castShadow = true;
      chandelierGroup.add(mainLight);

      // Hanging crystals from center
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2;
        const crystal = new THREE.Mesh(
          new THREE.OctahedronGeometry(0.04),
          crystalMat
        );
        crystal.position.set(
          Math.cos(angle) * 0.2,
          -0.2,
          Math.sin(angle) * 0.2
        );
        crystal.scale.y = 2;
        chandelierGroup.add(crystal);
      }

      chandelierGroup.position.set(x, HALL_HEIGHT - 2, z);
      scene.add(chandelierGroup);
      return chandelierGroup;
    };

    // Place chandeliers along the center of the hall
    const chandelierPositions = [15, 0, -15, -30];
    chandelierPositions.forEach(z => {
      createChandelier(0, z);
    });

    // 5a. Ground Paths - Simple elegant runners from wall to floor marker
    SUBJECT_CHANNELS.forEach(subject => {
      // Calculate path dimensions
      const wallX = subject.side === 'left' ? -HALL_WIDTH / 2 : HALL_WIDTH / 2;
      const markerX = subject.spotX;
      const pathLength = Math.abs(markerX - wallX);
      const pathWidth = 2.0;
      const centerX = (wallX + markerX) / 2;

      // Main path runner - cream colored carpet
      const pathGeo = new THREE.PlaneGeometry(pathLength, pathWidth);
      const pathMat = new THREE.MeshBasicMaterial({
        color: 0xf0e8d8,
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide
      });
      const path = new THREE.Mesh(pathGeo, pathMat);
      path.rotation.x = -Math.PI / 2;
      path.position.set(centerX, 0.015, subject.z);
      scene.add(path);

      // Gold border - top edge
      const borderGeo = new THREE.PlaneGeometry(pathLength, 0.1);
      const borderMat = new THREE.MeshBasicMaterial({
        color: 0xc4a862,
        transparent: true,
        opacity: 0.5
      });
      const topBorder = new THREE.Mesh(borderGeo, borderMat);
      topBorder.rotation.x = -Math.PI / 2;
      topBorder.position.set(centerX, 0.018, subject.z + pathWidth / 2);
      scene.add(topBorder);

      // Gold border - bottom edge
      const bottomBorder = new THREE.Mesh(borderGeo, borderMat);
      bottomBorder.rotation.x = -Math.PI / 2;
      bottomBorder.position.set(centerX, 0.018, subject.z - pathWidth / 2);
      scene.add(bottomBorder);
    });

    // 5b. Floor Markers - Minimal black circular markers with dotted lines
    const interactionSpots = [];
    SUBJECT_CHANNELS.forEach(subject => {
      const spotGroup = new THREE.Group();

      // Simple black outer ring
      const outerRingGeo = new THREE.RingGeometry(0.9, 1.0, 32);
      const outerRingMat = new THREE.MeshBasicMaterial({
        color: 0x111111,
        transparent: true,
        opacity: 0.95,
        side: THREE.DoubleSide
      });
      const outerRing = new THREE.Mesh(outerRingGeo, outerRingMat);
      outerRing.rotation.x = -Math.PI / 2;
      spotGroup.add(outerRing);

      // Inner black circle
      const innerCircleGeo = new THREE.CircleGeometry(0.85, 32);
      const innerCircleMat = new THREE.MeshBasicMaterial({
        color: 0x1a1a1a,
        transparent: true,
        opacity: 0.9,
        side: THREE.DoubleSide
      });
      const innerCircle = new THREE.Mesh(innerCircleGeo, innerCircleMat);
      innerCircle.rotation.x = -Math.PI / 2;
      innerCircle.position.y = 0.005;
      spotGroup.add(innerCircle);

      // Small center dot - slightly lighter
      const centerGeo = new THREE.CircleGeometry(0.15, 16);
      const centerMat = new THREE.MeshBasicMaterial({
        color: 0x333333,
        transparent: true,
        opacity: 0.95,
        side: THREE.DoubleSide
      });
      const center = new THREE.Mesh(centerGeo, centerMat);
      center.rotation.x = -Math.PI / 2;
      center.position.y = 0.01;
      spotGroup.add(center);

      // Position the spot
      spotGroup.position.set(subject.spotX, 0.02, subject.z);

      // Store references for animation
      spotGroup.userData.innerCircle = innerCircle;
      spotGroup.userData.outerRing = outerRing;
      spotGroup.userData.center = center;
      spotGroup.userData.subjectId = subject.id;

      scene.add(spotGroup);
      interactionSpots.push({ group: spotGroup, subject });

      // Dotted line from floor marker to portrait - larger and more visible
      const wallX = subject.side === 'left' ? -HALL_WIDTH / 2 + 0.5 : HALL_WIDTH / 2 - 0.5;
      const startX = subject.spotX;
      const lineLength = Math.abs(wallX - startX);
      const dotCount = Math.floor(lineLength / 0.5); // Dot every 0.5 units

      for (let i = 1; i < dotCount; i++) {
        const progress = i / dotCount;
        const dotX = startX + (wallX - startX) * progress;

        // Larger, darker dots
        const dotGeo = new THREE.CircleGeometry(0.12, 12);
        const dotMat = new THREE.MeshBasicMaterial({
          color: 0x0a0a0a,
          transparent: false,
          side: THREE.DoubleSide
        });
        const dot = new THREE.Mesh(dotGeo, dotMat);
        dot.rotation.x = -Math.PI / 2;
        dot.position.set(dotX, 0.025, subject.z);
        scene.add(dot);
      }

      // Larger arrow head near the wall pointing to portrait
      const arrowX = subject.side === 'left' ? wallX + 0.4 : wallX - 0.4;
      const arrowShape = new THREE.Shape();
      if (subject.side === 'left') {
        arrowShape.moveTo(-0.25, 0);
        arrowShape.lineTo(0.15, 0.2);
        arrowShape.lineTo(0.15, -0.2);
      } else {
        arrowShape.moveTo(0.25, 0);
        arrowShape.lineTo(-0.15, 0.2);
        arrowShape.lineTo(-0.15, -0.2);
      }
      arrowShape.closePath();

      const arrowGeo = new THREE.ShapeGeometry(arrowShape);
      const arrowMat = new THREE.MeshBasicMaterial({
        color: 0x0a0a0a,
        transparent: false,
        side: THREE.DoubleSide
      });
      const arrow = new THREE.Mesh(arrowGeo, arrowMat);
      arrow.rotation.x = -Math.PI / 2;
      arrow.position.set(arrowX, 0.025, subject.z);
      scene.add(arrow);
    });

    // Store interaction spots in state ref
    stateRef.current.interactionSpots = interactionSpots;

    // 6. Socrates 3D Sculpture
    const socratesGroup = new THREE.Group();
    socratesGroup.position.set(0, 0, -HALL_DEPTH / 2 + 6);
    scene.add(socratesGroup);

    // Warm museum-style ceiling spotlight on Socrates
    const socratesZ = -HALL_DEPTH / 2 + 6;

    // Main warm spotlight from ceiling - extremely bright
    const spotlight = new THREE.SpotLight(0xffaa44, 100, 80, Math.PI / 10, 0.2, 1);
    spotlight.position.set(0, HALL_HEIGHT - 0.5, socratesZ);
    spotlight.target.position.set(0, 5, socratesZ);
    spotlight.castShadow = true;
    spotlight.shadow.mapSize.width = 2048;
    spotlight.shadow.mapSize.height = 2048;
    scene.add(spotlight);
    scene.add(spotlight.target);

    // Second spotlight - wider coverage
    const spotlight2 = new THREE.SpotLight(0xffcc55, 60, 70, Math.PI / 6, 0.4, 1);
    spotlight2.position.set(0, HALL_HEIGHT - 0.5, socratesZ);
    spotlight2.target.position.set(0, 3, socratesZ);
    scene.add(spotlight2);
    scene.add(spotlight2.target);

    // Glowing light source at ceiling
    const bulbGeo = new THREE.SphereGeometry(0.6, 16, 16);
    const bulbMat = new THREE.MeshBasicMaterial({ color: 0xffffdd });
    const bulb = new THREE.Mesh(bulbGeo, bulbMat);
    bulb.position.set(0, HALL_HEIGHT - 0.5, socratesZ);
    scene.add(bulb);

    // Ceiling fixture/housing
    const fixtureGeo = new THREE.CylinderGeometry(0.7, 0.9, 0.5, 16);
    const fixtureMat = new THREE.MeshStandardMaterial({ color: 0x3a4a30, metalness: 0.8, roughness: 0.3 }); // Dark olive
    const fixture = new THREE.Mesh(fixtureGeo, fixtureMat);
    fixture.position.set(0, HALL_HEIGHT - 0.1, socratesZ);
    scene.add(fixture);

    // Glowing warm circle on the floor under Socrates
    const glowCircleGeo = new THREE.CircleGeometry(5, 32);
    const glowCircleMat = new THREE.MeshBasicMaterial({
      color: 0xffcc66,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
    });
    const glowCircle = new THREE.Mesh(glowCircleGeo, glowCircleMat);
    glowCircle.rotation.x = -Math.PI / 2;
    glowCircle.position.set(0, 0.05, socratesZ);
    scene.add(glowCircle);

    // Strong point lights bathing Socrates in warm light
    const warmGlow1 = new THREE.PointLight(0xffbb44, 10, 20, 2);
    warmGlow1.position.set(0, 10, socratesZ);
    scene.add(warmGlow1);

    const warmGlow2 = new THREE.PointLight(0xffcc66, 8, 15, 2);
    warmGlow2.position.set(3, 6, socratesZ);
    scene.add(warmGlow2);

    const warmGlow3 = new THREE.PointLight(0xffcc66, 8, 15, 2);
    warmGlow3.position.set(-3, 6, socratesZ);
    scene.add(warmGlow3);

    const warmGlow4 = new THREE.PointLight(0xffdd77, 6, 12, 2);
    warmGlow4.position.set(0, 5, socratesZ + 3);
    scene.add(warmGlow4);

    // Create elegant Greek-style pedestal for the bust
    const marbleMat = new THREE.MeshStandardMaterial({
      color: 0xf5f0e8,
      roughness: 0.25,
      metalness: 0.05,
    });
    const goldAccentMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      roughness: 0.3,
      metalness: 0.7,
    });

    // Base platform (wide, low)
    const basePlatform = new THREE.Mesh(
      new THREE.BoxGeometry(3.5, 0.25, 3.5),
      marbleMat
    );
    basePlatform.position.y = 0.125;
    basePlatform.receiveShadow = true;
    socratesGroup.add(basePlatform);

    // Gold trim on base
    const baseTrim = new THREE.Mesh(
      new THREE.BoxGeometry(3.6, 0.08, 3.6),
      goldAccentMat
    );
    baseTrim.position.y = 0.29;
    socratesGroup.add(baseTrim);

    // Lower plinth (square with beveled look)
    const lowerPlinth = new THREE.Mesh(
      new THREE.BoxGeometry(2.8, 0.5, 2.8),
      marbleMat
    );
    lowerPlinth.position.y = 0.58;
    lowerPlinth.castShadow = true;
    socratesGroup.add(lowerPlinth);

    // Main column (octagonal for Greek style)
    const columnGeo = new THREE.CylinderGeometry(1.2, 1.4, 2, 8);
    const column = new THREE.Mesh(columnGeo, marbleMat);
    column.position.y = 1.83;
    column.castShadow = true;
    column.receiveShadow = true;
    socratesGroup.add(column);

    // Column fluting effect (vertical grooves)
    for (let i = 0; i < 8; i++) {
      const angle = (i / 8) * Math.PI * 2;
      const flute = new THREE.Mesh(
        new THREE.BoxGeometry(0.08, 1.9, 0.15),
        marbleMat
      );
      flute.position.set(
        Math.cos(angle) * 1.25,
        1.83,
        Math.sin(angle) * 1.25
      );
      flute.rotation.y = angle;
      socratesGroup.add(flute);
    }

    // Upper capital (decorative top)
    const capital = new THREE.Mesh(
      new THREE.BoxGeometry(2.6, 0.3, 2.6),
      marbleMat
    );
    capital.position.y = 2.98;
    capital.castShadow = true;
    socratesGroup.add(capital);

    // Gold ring accent on capital
    const capitalRing = new THREE.Mesh(
      new THREE.TorusGeometry(1.3, 0.06, 8, 32),
      goldAccentMat
    );
    capitalRing.rotation.x = Math.PI / 2;
    capitalRing.position.y = 3.15;
    socratesGroup.add(capitalRing);

    // Top platform for bust
    const topPlatform = new THREE.Mesh(
      new THREE.CylinderGeometry(1.4, 1.5, 0.2, 32),
      marbleMat
    );
    topPlatform.position.y = 3.23;
    topPlatform.receiveShadow = true;
    socratesGroup.add(topPlatform);

    // Load 3D Socrates bust model (GLTF format)
    setLoadingStatus('Loading Socrates sculpture...');
    const gltfLoader = new GLTFLoader();
    gltfLoader.load('/models/socrates/socrates.glb', (gltf) => {
      console.log('Socrates bust loaded!');
      setLoadingStages(prev => ({ ...prev, socratesModel: true }));
      setLoadingStatus('Socrates sculpture loaded');
      const model = gltf.scene;

      // Calculate bounding box
      const box = new THREE.Box3().setFromObject(model);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());

      console.log('Socrates size:', size.x, size.y, size.z);

      // Scale to fit on pedestal (much bigger and more imposing)
      const targetHeight = 9;
      const scaleFactor = targetHeight / size.y;
      model.scale.setScalar(scaleFactor);

      // Recalculate box after scaling
      model.updateMatrixWorld(true);
      box.setFromObject(model);

      // Center horizontally and place on pedestal top (pedestal top is at y=3.33)
      model.position.x = -box.getCenter(new THREE.Vector3()).x;
      model.position.z = -box.getCenter(new THREE.Vector3()).z;
      model.position.y = 3.33 - box.min.y;

      // Face towards the player (rotate -90 degrees from current)
      model.rotation.y = -Math.PI / 2;

      // Enable shadows
      model.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true;
          child.receiveShadow = true;
        }
      });

      socratesGroup.add(model);
      stateRef.current.socratesBust = model;
      stateRef.current.socratesBustBaseY = model.position.y;

      // Add subtle glow effect
      const glowLight = new THREE.PointLight(0x88ccff, 0.8, 10);
      glowLight.position.set(0, 5, 2);
      socratesGroup.add(glowLight);
      stateRef.current.socratesGlow = glowLight;

      console.log('Socrates sculpture ready!');
    }, (progress) => {
      if (progress.total > 0) {
        console.log('Loading Socrates:', Math.round((progress.loaded / progress.total) * 100) + '%');
      }
    }, (error) => {
      console.error('Error loading Socrates:', error);
      // Still mark as loaded to not block the app
      setLoadingStages(prev => ({ ...prev, socratesModel: true }));
      setLoadingStatus('Socrates load failed - continuing...');
    });

    camera.position.set(0, 5, 12);

    // Setup post-processing
    const composer = new EffectComposer(renderer);

    // Render pass
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);

    // Very subtle bloom for realism - almost none
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight),
      0.08,  // very low intensity for subtle light glow
      0.3,   // tight radius
      0.95   // high threshold - only brightest areas
    );
    composer.addPass(bloomPass);

    // FXAA anti-aliasing
    const fxaaPass = new ShaderPass(FXAAShader);
    fxaaPass.uniforms['resolution'].value.set(1 / window.innerWidth, 1 / window.innerHeight);
    composer.addPass(fxaaPass);

    // Output pass
    const outputPass = new OutputPass();
    composer.addPass(outputPass);

    stateRef.current = {
      ...stateRef.current,
      scene, camera, renderer, paintings, socrates: socratesGroup, composer
    };

    // Mark scene as ready
    setLoadingStages(prev => ({ ...prev, scene: true }));
    setLoadingStatus('Gallery ready');

    // Input handlers
    const handleKeyDown = (e) => { stateRef.current.keys[e.key.toLowerCase()] = true; };
    const handleKeyUp = (e) => { stateRef.current.keys[e.key.toLowerCase()] = false; };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    // Animation loop with 144 FPS cap for high refresh rate displays
    let animId;
    let lastFrameTime = 0;
    const targetFPS = 144;
    const frameInterval = 1000 / targetFPS;

    const animate = (currentTime) => {
      animId = requestAnimationFrame(animate);

      // Frame rate limiting
      const elapsed = currentTime - lastFrameTime;
      if (elapsed < frameInterval) return;
      lastFrameTime = currentTime - (elapsed % frameInterval);

      const s = stateRef.current;
      if (!s.player) return;

      const dt = Math.min(s.clock.getDelta(), 0.1);  // Cap delta to prevent jumps
      const t = s.clock.getElapsedTime();

      // Update FBX animation mixer
      if (s.mixer) {
        s.mixer.update(dt);
      }

      // Movement - W/Up moves FORWARD (towards Socrates at negative Z)
      const moveSpeed = 35; // Slower, more controllable speed
      const friction = 0.85; // More friction = stops faster when key released
      if (s.keys['w'] || s.keys['arrowup']) s.vel.z -= moveSpeed * dt;    // Forward = -Z
      if (s.keys['s'] || s.keys['arrowdown']) s.vel.z += moveSpeed * dt;  // Backward = +Z
      if (s.keys['a'] || s.keys['arrowleft']) s.vel.x -= moveSpeed * dt;  // Left = -X
      if (s.keys['d'] || s.keys['arrowright']) s.vel.x += moveSpeed * dt; // Right = +X

      s.vel.multiplyScalar(friction);
      s.player.position.add(s.vel.clone().multiplyScalar(dt));
      s.player.position.x = THREE.MathUtils.clamp(s.player.position.x, -HALL_WIDTH / 2 + 2, HALL_WIDTH / 2 - 2);
      s.player.position.z = THREE.MathUtils.clamp(s.player.position.z, -HALL_DEPTH / 2 + 10, HALL_DEPTH / 2 - 5);

      const speed = s.vel.length();
      const isMoving = speed > 0.1;

      // Control walk animation using timeScale for smooth transitions
      if (s.walkAction) {
        // Smoothly transition timeScale instead of abrupt pause/play
        const targetTimeScale = isMoving ? 1 : 0;
        s.walkAction.timeScale = THREE.MathUtils.lerp(s.walkAction.timeScale, targetTimeScale, 0.1);
      }

      // Rotate player to face movement direction
      if (isMoving) {
        // Character faces the direction of movement
        const targetAngle = Math.atan2(s.vel.x, s.vel.z);
        s.player.rotation.y = THREE.MathUtils.lerp(s.player.rotation.y, targetAngle, 0.15);
      }

      // Camera follow (Original)
      const targetCam = new THREE.Vector3(s.player.position.x * 0.6, 5.5, s.player.position.z + 9);
      s.camera.position.lerp(targetCam, 0.08);
      s.camera.lookAt(s.player.position.x, 2.5, s.player.position.z - 4);

      // Socrates animation effects when player is near
      if (s.socrates && s.socratesBust) {
        const distToSocrates = s.player.position.distanceTo(s.socrates.position);
        const isNearSocrates = distToSocrates < 15;
        const baseY = s.socratesBustBaseY || 3;

        if (isNearSocrates) {
          // Subtle bobbing effect (like breathing/talking)
          s.socratesBust.position.y = baseY + Math.sin(t * 2) * 0.05;
          // Keep facing forward - don't rotate, just bob
        }

        // Pulsing glow effect
        if (s.socratesGlow) {
          const glowIntensity = isNearSocrates ? 1.0 + Math.sin(t * 3) * 0.4 : 0.4;
          s.socratesGlow.intensity = THREE.MathUtils.lerp(s.socratesGlow.intensity, glowIntensity, 0.1);
        }
      }

      // ====== COSMIC ANIMATIONS ======

      // Animate blinking stars (realistic twinkling with flicker)
      if (s.featuredStars) {
        s.featuredStars.forEach((star) => {
          const data = star.userData;

          // Handle random flicker events
          data.nextFlicker -= dt;
          if (data.nextFlicker <= 0 && !data.flickering) {
            data.flickering = true;
            data.flickerEnd = t + 0.1 + Math.random() * 0.2;
          }
          if (data.flickering && t > data.flickerEnd) {
            data.flickering = false;
            data.nextFlicker = 2 + Math.random() * 8;
          }

          // Calculate twinkle based on type
          let twinkle;
          if (data.flickering) {
            // Rapid flicker during flicker event
            twinkle = Math.sin(t * 30) * 0.5;
          } else if (data.blinkType === 0) {
            // Slow gentle pulse
            twinkle = Math.sin(t * data.twinkleSpeed + data.twinklePhase);
          } else if (data.blinkType === 1) {
            // Medium regular twinkle
            twinkle = Math.sin(t * data.twinkleSpeed + data.twinklePhase) *
                      Math.sin(t * data.twinkleSpeed * 0.3 + data.twinklePhase);
          } else {
            // Fast shimmer
            twinkle = Math.sin(t * data.twinkleSpeed + data.twinklePhase) *
                      (0.5 + Math.sin(t * data.twinkleSpeed * 2) * 0.5);
          }

          const scale = data.baseScale * (0.7 + twinkle * 0.5);
          star.scale.set(scale, scale, 1);
          star.material.opacity = data.baseOpacity * (0.5 + twinkle * 0.5);
        });
      }

      // Animate shooting stars / meteors
      if (s.shootingStars) {
        s.shootingStars.forEach((meteor) => {
          const data = meteor.userData;

          if (!data.active) {
            data.nextTrigger -= dt;
            if (data.nextTrigger <= 0) {
              // Trigger new shooting star
              data.active = true;
              data.progress = 0;
              data.startX = (Math.random() - 0.5) * 20;
              data.startY = 12 + Math.random() * 6;
              data.startZ = -HALL_DEPTH / 2 - 5;
              data.dirX = (Math.random() - 0.5) * 0.5;
              data.dirY = -0.3 - Math.random() * 0.3;
              data.dirZ = 0.1;
              data.speed = 15 + Math.random() * 10;
              meteor.material.opacity = 1;
            }
          } else {
            data.progress += dt * data.speed;
            const positions = meteor.geometry.attributes.position.array;

            for (let j = 0; j < data.trailLength; j++) {
              const trailOffset = j * 0.15;
              const px = data.startX + data.dirX * (data.progress - trailOffset);
              const py = data.startY + data.dirY * (data.progress - trailOffset);
              const pz = data.startZ + data.dirZ * (data.progress - trailOffset);
              positions[j * 3] = px;
              positions[j * 3 + 1] = py;
              positions[j * 3 + 2] = pz;
            }
            meteor.geometry.attributes.position.needsUpdate = true;

            // Fade out and reset
            if (data.progress > 8) {
              meteor.material.opacity = Math.max(0, 1 - (data.progress - 8) / 2);
              if (data.progress > 10) {
                data.active = false;
                data.nextTrigger = 3 + Math.random() * 8;
                meteor.material.opacity = 0;
              }
            }
          }
        });
      }

      // Animate rotating galaxy (smooth circular rotation facing audience)
      if (s.galaxy) {
        s.galaxy.rotation.z += 0.1 * dt; // Smooth rotation around Z axis (facing camera)
      }

      // Pulse galaxy core glow with breathing effect
      if (s.galaxyCore) {
        const corePulse = Math.sin(t * 1.2) * 0.2 + 1;
        s.galaxyCore.scale.set(5 * corePulse, 5 * corePulse, 1);
        s.galaxyCore.material.opacity = 0.8 + Math.sin(t * 1.8) * 0.15;
      }

      // Animate star field with slow drift
      if (s.starField) {
        s.starField.rotation.y += 0.003 * dt;
      }

      // Animate wisdom symbol (subtle glow pulse)
      if (s.wisdomSymbol) {
        const glowPulse = Math.sin(t * 1.5) * 0.1;
        s.wisdomSymbol.scale.setScalar(1 + glowPulse * 0.1);
      }

      // Proximity detection for interaction spots (floor markers)
      let closest = null;
      let isOnSpot = false;

      // Check each interaction spot
      if (s.interactionSpots) {
        s.interactionSpots.forEach(spot => {
          const spotPos = spot.group.position;
          const playerPos2D = new THREE.Vector2(s.player.position.x, s.player.position.z);
          const spotPos2D = new THREE.Vector2(spotPos.x, spotPos.z);
          const distToSpot = playerPos2D.distanceTo(spotPos2D);

          // Check if player is standing on the spot
          if (distToSpot < INTERACTION_SPOT_RADIUS) {
            closest = { ...spot.subject, type: 'subject' };
            isOnSpot = true;

            // Animate spot when standing on it - subtle pulse
            const pulse = Math.sin(t * 4) * 0.5 + 0.5;

            if (spot.group.userData.outerRing) {
              spot.group.userData.outerRing.material.opacity = 1;
              spot.group.userData.outerRing.scale.setScalar(1 + pulse * 0.08);
            }
            if (spot.group.userData.innerCircle) {
              spot.group.userData.innerCircle.material.opacity = 0.95;
            }
            if (spot.group.userData.center) {
              spot.group.userData.center.material.opacity = 1;
              spot.group.userData.center.scale.setScalar(1 + pulse * 0.15);
            }
          } else if (distToSpot < 3) {
            // Near the spot - slight highlight
            if (spot.group.userData.outerRing) {
              spot.group.userData.outerRing.material.opacity = 0.98;
              spot.group.userData.outerRing.scale.setScalar(1);
            }
            if (spot.group.userData.innerCircle) {
              spot.group.userData.innerCircle.material.opacity = 0.92;
            }
            if (spot.group.userData.center) {
              spot.group.userData.center.material.opacity = 0.98;
              spot.group.userData.center.scale.setScalar(1);
            }
          } else {
            // Default state
            if (spot.group.userData.outerRing) {
              spot.group.userData.outerRing.material.opacity = 0.95;
              spot.group.userData.outerRing.scale.setScalar(1);
            }
            if (spot.group.userData.innerCircle) {
              spot.group.userData.innerCircle.material.opacity = 0.9;
            }
            if (spot.group.userData.center) {
              spot.group.userData.center.material.opacity = 0.95;
              spot.group.userData.center.scale.setScalar(1);
            }
          }
        });
      }

      // Also animate the corresponding portal frame when on spot
      s.paintings.forEach(p => {
        const isThisSubjectActive = closest && closest.id === p.data.id && isOnSpot;

        if (isThisSubjectActive) {
          // Intensify glow light when player is on the spot
          if (p.group.userData.glowLight) {
            p.group.userData.glowLight.intensity = 1.0 + Math.sin(t * 4) * 0.4;
          }
        } else {
          // Reset to subtle state
          if (p.group.userData.glowLight) {
            p.group.userData.glowLight.intensity = p.group.userData.baseGlowIntensity;
          }
        }
      });

      // Check if player is near Socrates and trigger greeting
      if (s.socrates) {
        const distToSocrates = s.player.position.distanceTo(s.socrates.position);
        if (distToSocrates < SOCRATES_APPROACH_DISTANCE && !greetingTriggeredRef.current) {
          greetingTriggeredRef.current = true;
          triggerSocratesGreeting();
        }
        if (distToSocrates < 12) {
          closest = { id: 'general', name: 'General Wisdom', icon: '🌟', description: 'Ask anything - Socratic dialogue on any topic', type: 'general' };
        }
      }

      // Only update state if focus actually changed (prevents constant re-renders)
      const currentFocusId = stateRef.current.lastFocusId;
      const newFocusId = closest?.id || null;
      if (currentFocusId !== newFocusId) {
        stateRef.current.lastFocusId = newFocusId;
        setFocusEntity(closest);
      }

      // Animate twinkling ceiling stars
      if (s.starGroup) {
        s.starGroup.children.forEach(star => {
          if (star.userData.baseSize) {
            const twinkle = Math.sin(t * star.userData.twinkleSpeed + star.userData.twinkleOffset);
            const scale = 1 + twinkle * 0.3;
            star.scale.setScalar(scale);
          }
        });
      }

      // Use composer for post-processing
      if (s.composer) {
        s.composer.render();
      } else {
        s.renderer.render(s.scene, s.camera);
      }
    };
    animate(0);  // Start with initial timestamp

    // Resize handler
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      if (stateRef.current.composer) {
        stateRef.current.composer.setSize(window.innerWidth, window.innerHeight);
        // Update FXAA resolution
        fxaaPass.uniforms['resolution'].value.set(1 / window.innerWidth, 1 / window.innerHeight);
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (containerRef.current) containerRef.current.innerHTML = "";
    };
  }, [isLoading]);

  // Handle showing session choice modal for a subject
  const handleSubjectClick = (entity) => {
    if (entity.type === 'general') {
      // General wisdom goes directly to chat
      navigate('/app/scoratis?subject=general');
    } else {
      // Show session choice modal for subjects
      setSelectedSubject(entity);
      setShowSessionChoice(true);
    }
  };

  // Handle session choice - continue or start fresh
  const handleSessionChoice = (choice) => {
    if (!selectedSubject) return;

    const subjectId = selectedSubject.id;

    if (choice === 'fresh') {
      // Start fresh - new session
      const newSessionId = `${subjectId}_${Date.now()}`;
      localStorage.setItem(`scoratis_last_session_${subjectId}`, newSessionId);
      navigate(`/app/scoratis?subject=${subjectId}&session=${newSessionId}&fresh=true`);
    } else {
      // Continue previous session
      const lastSession = localStorage.getItem(`scoratis_last_session_${subjectId}`);
      const sessionId = lastSession || `${subjectId}_${Date.now()}`;
      localStorage.setItem(`scoratis_last_session_${subjectId}`, sessionId);
      navigate(`/app/scoratis?subject=${subjectId}&session=${sessionId}`);
    }

    setShowSessionChoice(false);
    setSelectedSubject(null);
  };

  // Close session choice modal
  const handleCloseSessionChoice = () => {
    setShowSessionChoice(false);
    setSelectedSubject(null);
  };

  return (
    <>
      {/* Elegant Loading Screen with Zoom Transition */}
      {loadingPhase !== 'gallery' && (
        <div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center overflow-hidden"
          style={{
            backgroundColor: '#f5f0e6',
            transition: 'transform 1.5s cubic-bezier(0.4, 0, 0.2, 1), opacity 1.5s cubic-bezier(0.4, 0, 0.2, 1), filter 1.5s cubic-bezier(0.4, 0, 0.2, 1)',
            transform: loadingPhase === 'zooming' ? 'scale(15)' : 'scale(1)',
            opacity: loadingPhase === 'zooming' ? 0 : 1,
            filter: loadingPhase === 'zooming' ? 'blur(20px)' : 'blur(0px)',
          }}
        >
          {/* Subtle radial glow background */}
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] rounded-full pointer-events-none"
            style={{
              background: 'radial-gradient(circle, rgba(107, 124, 94, 0.08) 0%, transparent 70%)',
              opacity: loadingPhase === 'zooming' ? 0 : 1,
              transition: 'opacity 0.5s ease-out'
            }}
          />

          {/* Main content container - ALL visible from start */}
          <div
            className="text-center max-w-2xl px-8 relative z-10"
            style={{
              transition: 'transform 0.8s ease-out, opacity 0.8s ease-out',
              transform: loadingPhase === 'zooming' ? 'translateY(-50px)' : 'translateY(0)',
            }}
          >
            {/* Academy name */}
            <p
              className="text-sm tracking-[0.4em] uppercase mb-8"
              style={{ color: '#6b7c5e', fontWeight: 500 }}
            >
              Socratic Academy
            </p>

            {/* Decorative line */}
            <div className="flex items-center justify-center gap-4 mb-10">
              <div className="w-16 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
              <div className="w-2 h-2 rotate-45" style={{ backgroundColor: '#b8860b' }} />
              <div className="w-16 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
            </div>

            {/* Main Quote */}
            <h1
              className="text-4xl md:text-5xl lg:text-6xl font-light leading-tight mb-4"
              style={{
                fontFamily: 'Georgia, "Times New Roman", serif',
                color: '#3d4a35',
                letterSpacing: '-0.02em'
              }}
            >
              The unexamined life is
            </h1>
            <h1
              className="text-4xl md:text-5xl lg:text-6xl italic mb-12"
              style={{
                fontFamily: 'Georgia, "Times New Roman", serif',
                color: '#6b7c5e'
              }}
            >
              not worth living.
            </h1>

            {/* Loading section - single unified view */}
            <div
              className={`w-72 mx-auto transition-all duration-500 ${
                loadingPhase === 'zooming' ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
              }`}
            >
              {/* Loading/Entering text */}
              <div className="flex items-center justify-center gap-2 mb-4">
                {loadingPhase === 'ready' && (
                  <span className="w-2 h-2 rounded-full bg-[#6b7c5e] animate-pulse" />
                )}
                <p
                  className="text-sm text-center tracking-wide"
                  style={{ color: loadingPhase === 'ready' ? '#6b7c5e' : '#8a8a7a', fontFamily: 'Georgia, serif' }}
                >
                  {loadingPhase === 'ready' ? 'Entering...' : `Loading Scoratis... ${loadingProgress}%`}
                </p>
              </div>

              {/* Progress bar */}
              <div
                className="h-[3px] rounded-full overflow-hidden"
                style={{ backgroundColor: 'rgba(107, 124, 94, 0.15)' }}
              >
                <div
                  className="h-full rounded-full relative overflow-hidden transition-all duration-700 ease-out"
                  style={{
                    width: `${loadingProgress}%`,
                    background: 'linear-gradient(90deg, #6b7c5e 0%, #8a9a7a 50%, #b8860b 100%)'
                  }}
                >
                  {/* Shimmer effect */}
                  <div
                    className="absolute inset-0 animate-shimmer"
                    style={{
                      background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.5) 50%, transparent 100%)',
                      backgroundSize: '200% 100%'
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Bottom attribution */}
          <div className="absolute bottom-8 flex items-center gap-3">
            <div className="w-8 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
            <span
              className="text-xs tracking-[0.2em] uppercase"
              style={{ color: '#a0a090', fontFamily: 'Georgia, serif' }}
            >
              Socrates
            </span>
            <div className="w-8 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
          </div>
        </div>
      )}

      {/* Main Gallery */}
      <div
        className={`relative w-full h-screen bg-[#f5f0e6] text-[#4a5a40] font-sans overflow-hidden transition-opacity duration-1000 ${
          loadingPhase === 'gallery' ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ visibility: loadingPhase === 'loading' ? 'hidden' : 'visible' }}
      >
        {/* 3D Canvas */}
        <div ref={containerRef} className="absolute inset-0 z-0" />

        {/* UI Overlay (Original Style) */}
        <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-12">
          <header className="flex justify-between items-start">
            {/* Clean header - no UI clutter */}
          </header>

          {focusEntity && (
            <div className="flex flex-col items-center justify-center animate-in fade-in slide-in-from-bottom-8 duration-500">
              <div className="bg-[#faf6ed] border border-[#d4cfb8] p-10 rounded-[2rem] text-center max-w-md shadow-2xl">
                {/* Decorative top line */}
                <div className="flex items-center justify-center gap-3 mb-6">
                  <div className="w-12 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
                  <div className="w-2 h-2 rotate-45" style={{ backgroundColor: focusEntity.color || '#b8860b' }} />
                  <div className="w-12 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
                </div>

                {/* Subject Icon */}
                <div className="flex justify-center mb-4">
                  <span className="text-5xl">{focusEntity.icon}</span>
                </div>

                {/* Subject Name - elegant serif */}
                <h2 className="text-2xl font-serif italic tracking-tight mb-2 text-[#4a5a40]">
                  {focusEntity.name}
                </h2>

                {/* Colored accent line */}
                <div className="w-16 h-1 mx-auto mb-4 rounded-full" style={{ backgroundColor: focusEntity.color || '#6b7c5e' }} />

                {/* Description */}
                <p className="text-[#6b7c5e] text-sm mb-6 px-4 font-medium leading-relaxed" style={{ fontFamily: 'Georgia, serif' }}>
                  {focusEntity.description}
                </p>

                {/* Enter Button - gallery theme */}
                <button
                  onClick={() => handleSubjectClick(focusEntity)}
                  className="pointer-events-auto bg-[#4a5a40] text-[#f5f0e6] px-10 py-3 rounded-full font-bold text-xs uppercase tracking-widest hover:bg-[#3a4a30] transition-all transform active:scale-95 shadow-lg"
                >
                  Begin Learning
                </button>

                {/* Bottom decorative */}
                <div className="flex items-center justify-center gap-2 mt-6">
                  <div className="w-6 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
                  <span className="text-[10px] tracking-[0.2em] uppercase text-[#a0a090]">Standing on marker</span>
                  <div className="w-6 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
                </div>
              </div>
            </div>
          )}

          <footer className="flex flex-col items-center gap-2">
            {modelStatus === 'loading' && (
              <div className="bg-[#faf6ed]/90 px-4 py-2 rounded-lg shadow-sm border border-[#d4cfb8]">
                <span className="text-xs text-[#6b7c5e]">Loading Character...</span>
              </div>
            )}
            {modelStatus === 'error' && (
              <div className="bg-[#fdf2f2] border border-[#e5c5c5] px-4 py-2 rounded-lg">
                <span className="text-xs text-[#9a5a5a]">Model failed to load - check console</span>
              </div>
            )}
            <span className="text-[10px] uppercase tracking-[0.5em] font-bold text-[#4a5a40] opacity-40">Walk to floor markers to enter subjects</span>
          </footer>
        </div>
      </div>

      {/* Socrates Greeting Dialog */}
      {showWelcomeDialog && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-[#faf6ed] border border-[#d4cfb8] rounded-2xl p-8 max-w-lg mx-4 shadow-2xl animate-in zoom-in-95 duration-500">
            {/* Greeting text */}
            <p
              className="text-lg leading-relaxed mb-8 text-center"
              style={{ color: '#4a5a40', fontFamily: 'Georgia, serif' }}
            >
              "{greetingText}"
            </p>

            {/* Buttons */}
            <div className="flex flex-col items-center gap-4">
              <button
                onClick={handleEnterChat}
                className="group flex items-center gap-3 bg-gradient-to-r from-[#4a5a40] to-[#3d4a35] text-[#f5f0e6] px-10 py-4 rounded-full font-bold text-sm uppercase tracking-widest hover:from-[#3d4a35] hover:to-[#2d3a25] transition-all transform hover:scale-105 active:scale-95 shadow-xl"
              >
                <MessageCircle className="w-5 h-5 group-hover:animate-pulse" />
                Begin Dialogue
              </button>

              <button
                onClick={handleDeclineChat}
                className="text-xs text-[#8a8a7a] hover:text-[#6b7c5e] transition-colors uppercase tracking-wider"
              >
                Continue Exploring
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session Choice Modal - Elegant Gallery Theme */}
      {showSessionChoice && selectedSubject && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-[#faf6ed] border border-[#d4cfb8] rounded-2xl p-8 max-w-sm mx-4 shadow-2xl animate-in zoom-in-95 duration-500">
            {/* Decorative top */}
            <div className="flex items-center justify-center gap-3 mb-5">
              <div className="w-10 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
              <div className="w-2 h-2 rotate-45" style={{ backgroundColor: selectedSubject.color }} />
              <div className="w-10 h-[1px]" style={{ backgroundColor: '#c4c0b4' }} />
            </div>

            {/* Subject Header */}
            <div className="text-center mb-6">
              <span className="text-4xl mb-2 block">{selectedSubject.icon}</span>
              <h3 className="text-xl font-serif italic text-[#4a5a40]">
                {selectedSubject.name}
              </h3>
              <div className="w-12 h-0.5 mx-auto mt-2 rounded-full" style={{ backgroundColor: selectedSubject.color }} />
            </div>

            {/* Question */}
            <p className="text-center text-sm text-[#6b7c5e] mb-5" style={{ fontFamily: 'Georgia, serif' }}>
              How would you like to begin your journey?
            </p>

            {/* Choice Buttons - Gallery theme */}
            <div className="flex flex-col gap-3">
              <button
                onClick={() => handleSessionChoice('continue')}
                className="w-full py-3 px-5 rounded-xl font-medium transition-all transform hover:scale-[1.02] active:scale-[0.98] border border-[#d4cfb8] text-left flex items-center gap-3 bg-white hover:bg-[#f5f0e6]"
              >
                <span className="text-xl">📖</span>
                <div>
                  <div className="font-semibold text-[#4a5a40] text-sm">Continue Previous</div>
                  <div className="text-xs text-[#8a8a7a]">Resume where you left off</div>
                </div>
              </button>

              <button
                onClick={() => handleSessionChoice('fresh')}
                className="w-full py-3 px-5 rounded-xl font-medium transition-all transform hover:scale-[1.02] active:scale-[0.98] text-left flex items-center gap-3 bg-[#4a5a40] hover:bg-[#3a4a30] text-[#f5f0e6]"
              >
                <span className="text-xl">✨</span>
                <div>
                  <div className="font-semibold text-sm">Start Fresh</div>
                  <div className="text-xs opacity-80">Begin a new dialogue</div>
                </div>
              </button>
            </div>

            {/* Cancel Button */}
            <button
              onClick={handleCloseSessionChoice}
              className="w-full mt-4 py-2 text-xs text-[#a0a090] hover:text-[#6b7c5e] transition-colors uppercase tracking-widest"
            >
              Continue Exploring
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default Gallery;
