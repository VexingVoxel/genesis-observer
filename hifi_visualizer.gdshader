shader_type canvas_item;

void fragment() {
    // Treat the Red channel as the Voxel ID (0-255)
    float voxel_id = texture(TEXTURE, UV).r * 255.0;
    
    vec4 color = vec4(0.0, 0.0, 0.0, 1.0); // Default black
    
    // Material Palette
    if (abs(voxel_id - 1.0) < 0.1) {
        color = vec4(0.45, 0.35, 0.25, 1.0); // Dirt (Brown)
    } 
    else if (abs(voxel_id - 2.0) < 0.1) {
        color = vec4(0.2, 0.7, 0.3, 1.0); // Grass (Green)
    }
    else if (abs(voxel_id - 3.0) < 0.1) {
        color = vec4(0.3, 0.5, 0.9, 1.0); // Water (Blue)
    }
    
    // Thermal Visualization (Optional Overlay)
    // float thermal = texture(TEXTURE, UV).b; // Blue channel is thermal
    // color.rgb += vec3(thermal * 0.5, 0.0, 0.0);
    
    COLOR = color;
}
