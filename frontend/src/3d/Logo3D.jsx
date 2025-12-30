import { Canvas, useFrame } from '@react-three/fiber'
import { useRef } from 'react'

function AnimatedOrb() {
  const meshRef = useRef()
  const coreRef = useRef()

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += 0.01
      meshRef.current.rotation.y += 0.015
    }
    if (coreRef.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.1
      coreRef.current.scale.set(scale, scale, scale)
    }
  })

  return (
    <>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1, 1]} />
        <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.8} />
      </mesh>
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.6, 16, 16]} />
        <meshBasicMaterial color="#d4af37" transparent opacity={0.5} />
      </mesh>
    </>
  )
}

export default function Logo3D() {
  return (
    <Canvas camera={{ position: [0, 0, 3], fov: 75 }}>
      <ambientLight intensity={0.5} />
      <AnimatedOrb />
    </Canvas>
  )
}
