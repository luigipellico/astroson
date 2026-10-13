import numpy as np

class ScanEngine:
    """Motore di calcolo per le linee di scansione continua in stile NASA"""
    @staticmethod
    def get_scan_coordinates(width, height, mode="horizontal", inverted=False):
        coords = []
        if mode == "horizontal":
            # Scansione orizzontale: la linea di scansione è VERTICALE e si sposta da sinistra a destra (passo ottimizzato a 3px)
            x_indices = np.arange(0, width, 3)
            if inverted:
                x_indices = x_indices[::-1]
            for x in x_indices:
                coords.append(('vertical_line', int(x)))
                
        elif mode == "vertical":
            y_indices = np.arange(0, height, 3)
            if inverted:
                y_indices = y_indices[::-1]
            for y in y_indices:
                coords.append(('horizontal_line', int(y)))
                
        elif mode == "concentric":
            center_x, center_y = width // 2, height // 2
            max_radius = int(np.hypot(center_x, center_y))
            r_indices = np.arange(0, max_radius, 3)
            if inverted:
                r_indices = r_indices[::-1]
            for r in r_indices:
                coords.append(('concentric_ring', int(r)))
                
        elif mode == "clock":
            center_x, center_y = width // 2, height // 2
            angles = np.linspace(0, 2 * np.pi, 180)
            if inverted:
                angles = angles[::-1]
            for angle in angles:
                coords.append(('clock_ray', float(angle)))
                
        return coords