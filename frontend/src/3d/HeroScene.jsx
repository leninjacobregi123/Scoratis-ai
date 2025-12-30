import { Canvas, useFrame } from '@react-three/fiber'
import { useRef, useMemo } from 'react'
import * as THREE from 'three'

function FloatingShapes() {
  const groupRef = useRef()

  const shapes = useMemo(() => {
    const items = []
    const colors = [0xffffff, 0xd4af37, 0x888888, 0xe8c860]

    for (let i = 0; i < 15; i++) {
      items.push({
        position: [
          (Math.random() - 0.5) * 12,
          (Math.random() - 0.5) * 8,
          (Math.random() - 0.5) * 8 - 3
        ],
        rotation: [Math.random() * Math.PI, Math.random() * Math.PI, 0],
        color: colors[Math.floor(Math.random() * colors.length)],
        type: Math.floor(Math.random() * 4),
        speed: Math.random() * 0.02 + 0.005,
        floatSpeed: Math.random() * 0.5 + 0.5,
        floatOffset: Math.random() * Math.PI * 2
      })
    }
    return items
  }, [])

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.children.forEach((child, i) => {
        const shape = shapes[i]
        child.rotation.x += shape.speed
        child.rotation.y += shape.speed * 0.7
        child.position.y = shape.position[1] + Math.sin(state.clock.elapsedTime * shape.floatSpeed + shape.floatOffset) * 0.3
      })
    }
  })

  return (
    <group ref={groupRef}>
      {shapes.map((shape, i) => (
        <mesh key={i} position={shape.position} rotation={shape.rotation}>
          {shape.type === 0 && <tetrahedronGeometry args={[0.4]} />}
          {shape.type === 1 && <octahedronGeometry args={[0.3]} />}
          {shape.type === 2 && <dodecahedronGeometry args={[0.25]} />}
          {shape.type === 3 && <torusGeometry args={[0.25, 0.08, 8, 16]} />}
          <meshBasicMaterial color={shape.color} wireframe transparent opacity={0.6} />
        </mesh>
      ))}
    </group>
  )
}

function MainOrb({ mousePosition }) {
  const orbRef = useRef()
  const coreRef = useRef()
  const ring1Ref = useRef()
  const ring2Ref = useRef()

  useFrame((state) => {
    if (orbRef.current) {
      orbRef.current.rotation.x += 0.005 + (mousePosition?.y || 0) * 0.01
      orbRef.current.rotation.y += 0.01 + (mousePosition?.x || 0) * 0.01
    }
    if (coreRef.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.1
      coreRef.current.scale.set(scale, scale, scale)
    }
    if (ring1Ref.current) {
      ring1Ref.current.rotation.z += 0.01
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.z -= 0.008
      ring2Ref.current.rotation.x += 0.005
    }
  })

  return (
    <group position={[2, 0, 0]}>
      <mesh ref={orbRef}>
        <icosahedronGeometry args={[1.8, 1]} />
        <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.8} />
      </mesh>
      <mesh ref={coreRef}>
        <sphereGeometry args={[1.3, 32, 32]} />
        <meshBasicMaterial color="#d4af37" transparent opacity={0.3} />
      </mesh>
      <mesh ref={ring1Ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.5, 0.04, 16, 100]} />
        <meshBasicMaterial color="#888888" transparent opacity={0.6} />
      </mesh>
      <mesh ref={ring2Ref} rotation={[Math.PI / 3, Math.PI / 4, 0]}>
        <torusGeometry args={[2.8, 0.03, 16, 100]} />
        <meshBasicMaterial color="#d4af37" transparent opacity={0.4} />
      </mesh>
    </group>
  )
}

function Particles() {
  const pointsRef = useRef()

  const particles = useMemo(() => {
    const positions = new Float32Array(300 * 3)
    const colors = new Float32Array(300 * 3)
    const colorOptions = [
      new THREE.Color(0xffffff),
      new THREE.Color(0xd4af37),
      new THREE.Color(0x888888),
      new THREE.Color(0xe8c860)
    ]

    for (let i = 0; i < 300; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 20
      positions[i * 3 + 1] = (Math.random() - 0.5) * 15
      positions[i * 3 + 2] = (Math.random() - 0.5) * 15 - 5

      const color = colorOptions[Math.floor(Math.random() * colorOptions.length)]
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b
    }

    return { positions, colors }
  }, [])

  useFrame(() => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += 0.001
    }
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={300}
          array={particles.positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={300}
          array={particles.colors}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial size={0.05} vertexColors transparent opacity={0.8} />
    </points>
  )
}

export default function HeroScene({ mousePosition }) {
  return (
    <Canvas camera={{ position: [0, 0, 8], fov: 75 }}>
      <ambientLight intensity={0.5} />
      <MainOrb mousePosition={mousePosition} />
      <FloatingShapes />
      <Particles />
    </Canvas>
  )
}
