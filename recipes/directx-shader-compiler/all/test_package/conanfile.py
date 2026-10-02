from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TEST_SPIRV"] = self.dependencies["directx-shader-compiler"].options.with_spirv
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindir, "test_package"), env="conanrun")
            if self.dependencies["directx-shader-compiler"].options.with_tools:
                shader = os.path.join(self.source_folder, "shader.hlsl")
                self.run(f'dxc -T ps_6_0 -E main "{shader}" -Fo shader.dxil', env="conanrun")
                if self.dependencies["directx-shader-compiler"].options.with_spirv:
                    self.run(f'dxc -spirv -T ps_6_0 -E main "{shader}" -Fo shader.spv', env="conanrun")
