// Module augmentation to ensure `Camera.reversedDepth` exists across @types/three versions
import 'three';

declare module 'three' {
  interface Camera {
    reversedDepth: boolean;
  }
}
