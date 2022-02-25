import os

import numpy as np
import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering


class PipelineView:
    """Controls display and user interface. All methods must run in the main thread."""

    def __init__(self, vfov=60, max_pcd_vertices=1 << 20, **callbacks):
        """Initialize.
        Args:
            vfov (float): Vertical field of view for the 3D scene.
            max_pcd_vertices (int): Maximum point clud verties for which memory
                is allocated.
            callbacks (dict of kwargs): Callbacks provided by the controller
                for various operations.
        """

        self.vfov = vfov
        self.max_pcd_vertices = max_pcd_vertices
        self.flag_normals = False

        gui.Application.instance.initialize()
        self.window = gui.Application.instance.create_window(
            "Open3D || Online RGBD Video Processing", 960, 512)
        # Called on window layout (eg: resize)
        self.window.set_on_layout(self.on_layout)
        self.window.set_on_close(callbacks['on_window_close'])

        self.pcd_material = o3d.visualization.rendering.MaterialRecord()
        self.pcd_material.shader = "defaultLit"
        # Set n_pixels displayed for each 3D point, accounting for HiDPI scaling
        self.pcd_material.point_size = int(2 * self.window.scaling)

        # 3D scene
        self.pcdview = gui.SceneWidget()
        self.window.add_child(self.pcdview)
        self.pcdview.enable_scene_caching(
            True)  # makes UI _much_ more responsive
        self.pcdview.scene = rendering.Open3DScene(self.window.renderer)
        self.pcdview.scene.set_background([1, 1, 1, 1])  # White background
        self.pcdview.scene.set_lighting(
            rendering.Open3DScene.LightingProfile.SOFT_SHADOWS, [0, -6, 0])
        # Point cloud bounds, depends on the sensor range
        self.pcd_bounds = o3d.geometry.AxisAlignedBoundingBox([-3, -3, 0],
                                                              [3, 3, 6])
        self.camera_view()  # Initially look from the camera
        em = self.window.theme.font_size

        # Options panel
        self.panel = gui.Vert(em, gui.Margins(em, em, em, em))
        self.panel.preferred_width = int(360 * self.window.scaling)
        self.window.add_child(self.panel)
        toggles = gui.Horiz(em)
        self.panel.add_child(toggles)

        self.video_size = (int(240 * self.window.scaling),
                           int(320 * self.window.scaling), 3)

        self.status_message = gui.Label("")
        self.panel.add_child(self.status_message)

        self.flag_exit = False
        self.flag_gui_init = False

    def update(self, frame_elements):
        """Update visualization with point cloud and images. Must run in main
        thread since this makes GUI calls.
        Args:
            frame_elements: dict {element_type: geometry element}.
                Dictionary of element types to geometry elements to be updated
                in the GUI:
                    'pcd': point cloud,
                    'color': rgb image (3 channel, uint8),
                    'depth': depth image (uint8),
                    'status_message': message
        """
        if not self.flag_gui_init:
            # Set dummy point cloud to allocate graphics memory
            dummy_pcd = o3d.t.geometry.PointCloud({
                'positions':
                    o3d.core.Tensor.zeros((self.max_pcd_vertices, 3),
                                          o3d.core.Dtype.Float32),
                'colors':
                    o3d.core.Tensor.zeros((self.max_pcd_vertices, 3),
                                          o3d.core.Dtype.Float32),
                'normals':
                    o3d.core.Tensor.zeros((self.max_pcd_vertices, 3),
                                          o3d.core.Dtype.Float32)
            })
            if self.pcdview.scene.has_geometry('pcd'):
                self.pcdview.scene.remove_geometry('pcd')

            self.pcd_material.shader = "normals" if self.flag_normals else "defaultLit"
            self.pcdview.scene.add_geometry('pcd', dummy_pcd, self.pcd_material)
            self.flag_gui_init = True

        # TODO(ssheorey) Switch to update_geometry() after #3452 is fixed
        if os.name == "nt" or os.name == "posix":
            self.pcdview.scene.remove_geometry('pcd')
            self.pcdview.scene.add_geometry('pcd', frame_elements['pcd'],
                                            self.pcd_material)
        else:
            update_flags = (rendering.Scene.UPDATE_POINTS_FLAG |
                            rendering.Scene.UPDATE_COLORS_FLAG |
                            (rendering.Scene.UPDATE_NORMALS_FLAG
                             if self.flag_normals else 0))
            self.pcdview.scene.scene.update_geometry('pcd',
                                                     frame_elements['pcd'],
                                                     update_flags)

        if 'status_message' in frame_elements:
            self.status_message.text = frame_elements["status_message"]

        self.pcdview.force_redraw()

    def camera_view(self):
        """Callback to reset point cloud view to the camera"""
        self.pcdview.setup_camera(self.vfov, self.pcd_bounds, [0, 0, 0])
        # Look at [0, 0, 1] from camera placed at [0, 0, 0] with Y axis
        # pointing at [0, -1, 0]
        self.pcdview.scene.camera.look_at([0, 0, 1], [0, 0, 0], [0, -1, 0])

    def birds_eye_view(self):
        """Callback to reset point cloud view to birds eye (overhead) view"""
        self.pcdview.setup_camera(self.vfov, self.pcd_bounds, [0, 0, 0])
        self.pcdview.scene.camera.look_at([0, 0, 1.5], [0, 3, 1.5], [0, -1, 0])

    def on_layout(self, layout_context):
        # The on_layout callback should set the frame (position + size) of every
        # child correctly. After the callback is done the window will layout
        # the grandchildren.
        """Callback on window initialize / resize"""
        frame = self.window.content_rect
        self.pcdview.frame = frame
        panel_size = self.panel.calc_preferred_size(layout_context,
                                                    self.panel.Constraints())
        self.panel.frame = gui.Rect(frame.get_right() - panel_size.width,
                                    frame.y, panel_size.width,
                                    panel_size.height)