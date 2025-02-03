bl_info = {
    "name": "Render Time Estimator",
    "author": "Samuel Francis (adapted by ChatGPT)",
    "version": (1, 1, 0),
    "blender": (4, 3, 0),
    "location": "Image Editor > Sidebar > Render ETA",
    "description": "Displays a modern header element and panel with a text-based progress bar and ETA during animation render.",
    "category": "Render",
}

import bpy, time

# Global variables
_frame_start = {}
_total_start = None
_first_rendered_frame = None
_last_frame_time = 0.0
_last_eta = "AWAITING RENDER"
_progress = 0.0
_is_rendering = False
_total_time = None
_avg_time = None
BAR_LENGTH = 25

def format_time(sec):
    """Format time into human-readable string."""
    if sec < 60:
        return f"{sec:.1f} sec"
    elif sec < 3600:
        return f"{sec/60:.1f} min"
    elif sec < 86400:
        return f"{int(sec // 3600)} hr {int((sec % 3600) // 60)} min"
    else:
        return f"{int(sec // 86400)} d {int((sec % 86400) // 3600)} hr"

def progress_bar(cur, total):
    """Generate a progress bar string."""
    pct = cur / total if total else 0
    filled = int(pct * BAR_LENGTH)
    bar = "█" * filled + "░" * (BAR_LENGTH - filled)
    return f"{cur}: [{bar}] {pct*100:5.1f}%"

def draw_header(self, context):
    """Display ETA & progress bar in Blender's header."""
    scene = context.scene
    layout = self.layout
    row = layout.row(align=True)
    row.alignment = 'RIGHT'
    
    if _is_rendering and _first_rendered_frame is not None:
        current_frame_index = scene.frame_current - _first_rendered_frame + 1
        total_frames = scene.frame_end - _first_rendered_frame + 1
        pb_text = progress_bar(current_frame_index, total_frames)

        if current_frame_index <= 2:
            status_msg = "Calculating ETA"
            alert_flag = True
        else:
            status_msg = _last_eta if _last_eta else "Calculating ETA"
            alert_flag = status_msg in {"Calculating ETA", "RENDER STOPPED"}
    else:
        status_msg = _last_eta
        pb_text = ""

    row.label(text="", icon='RENDER_ANIMATION')
    if pb_text:
        row.label(text=pb_text, icon='TIME')
    row.alert = alert_flag
    row.label(text="ETA: " + status_msg)

class RTE_PT_Panel(bpy.types.Panel):
    """ UI Panel in Image Editor sidebar. """
    bl_label = "Render Time Estimator"
    bl_idname = "RTE_PT_panel"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Render ETA'
    
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Render ETA Settings", icon='PREFERENCES')
        settings = context.scene.rte_settings
        col.prop(settings, "show_debug", text="Show Debug Messages")
        col.separator()
        col.label(text="Status:", icon='INFO')
        col.label(text="• " + _last_eta)
        if _total_time is not None:
            col.label(text="• Total Time: " + format_time(_total_time))
        if _avg_time is not None:
            col.label(text="• Avg Time/Frame: " + format_time(_avg_time))
        if _is_rendering:
            col.label(text="• Last Frame: " + format_time(_last_frame_time))

def reset_render_state():
    """Reset render state to ensure a fresh start."""
    global _frame_start, _total_start, _first_rendered_frame, _last_eta, _progress, _is_rendering, _total_time, _avg_time
    _frame_start.clear()
    _total_start = None
    _first_rendered_frame = None
    _last_eta = "AWAITING RENDER"
    _progress = 0.0
    _is_rendering = True
    _total_time = None
    _avg_time = None

def render_pre_handler(scene):
    """ Called before each frame renders, ensuring correct frame tracking. """
    global _total_start, _first_rendered_frame, _is_rendering
    cur = scene.frame_current

    if not _is_rendering:  # If it's a new render session
        reset_render_state()

    _frame_start[cur] = time.time()

    if _first_rendered_frame is None or cur < _first_rendered_frame:
        _first_rendered_frame = cur
        _total_start = time.time()

def render_post_handler(scene):
    """ Updates ETA after each frame is rendered. """
    global _last_frame_time, _last_eta, _progress
    cur = scene.frame_current

    if _first_rendered_frame is None:
        return  

    frame_index = cur - _first_rendered_frame + 1
    total_frames = scene.frame_end - _first_rendered_frame + 1
    t = time.time() - _frame_start.get(cur, time.time())
    _last_frame_time = t

    if frame_index >= 3:
        remaining = scene.frame_end - cur
        _last_eta = format_time(t * remaining)
    else:
        _last_eta = "Calculating ETA"

    _progress = frame_index / total_frames

def render_complete_handler(scene):
    """ Called when rendering is complete. Updates final render time. """
    global _last_eta, _is_rendering, _total_time, _avg_time
    total_frames = scene.frame_end - _first_rendered_frame + 1 if _first_rendered_frame is not None else 0
    total = time.time() - _total_start if _total_start else 0
    avg = total / total_frames if total_frames else 0
    _total_time = total
    _avg_time = avg
    _last_eta = f"RENDER COMPLETE | Total: {format_time(total)}, Avg: {format_time(avg)}"
    _is_rendering = False

def render_cancel_handler(scene):
    """ Called if render is cancelled. """
    global _last_eta, _is_rendering, _total_time, _avg_time
    _last_eta = "RENDER STOPPED"
    _is_rendering = False
    _total_time = None
    _avg_time = None

def register():
    bpy.utils.register_class(RTE_PT_Panel)
    bpy.types.IMAGE_HT_header.append(draw_header)
    bpy.app.handlers.render_pre.append(render_pre_handler)
    bpy.app.handlers.render_post.append(render_post_handler)
    bpy.app.handlers.render_complete.append(render_complete_handler)
    bpy.app.handlers.render_cancel.append(render_cancel_handler)

def unregister():
    bpy.utils.unregister_class(RTE_PT_Panel)
    bpy.types.IMAGE_HT_header.remove(draw_header)

if __name__ == "__main__":
    register()
