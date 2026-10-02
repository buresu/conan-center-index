from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


required_conan_version = ">=2.1"


class DirectXShaderCompilerConan(ConanFile):
    name = "directx-shader-compiler"
    description = "Compiler and library for translating HLSL shaders to DXIL and SPIR-V"
    license = "NCSA"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/microsoft/DirectXShaderCompiler"
    topics = ("hlsl", "dxil", "spirv", "shaders")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_spirv": [True, False],
        "with_tools": [True, False],
    }
    default_options = {
        "with_spirv": True,
        "with_tools": True,
    }
    short_paths = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.settings.os != "Windows":
            self.requires("directx-headers/1.619.5", headers=True, libs=False, run=False)
        if self.options.with_spirv:
            self.requires("spirv-headers/1.4.363.0")
            self.requires("spirv-tools/1.4.363.0")

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.os not in ("Windows", "Linux"):
            raise ConanInvalidConfiguration("This recipe supports Windows and Linux")
        if self.settings.os == "Windows" and self.settings.compiler != "msvc":
            raise ConanInvalidConfiguration("DXC requires MSVC on Windows")
        if self.options.with_spirv and self.dependencies["spirv-tools"].options.shared:
            raise ConanInvalidConfiguration("DXC needs spirv-tools/*:shared=False for SPIRV-Tools-opt")

    def validate_build(self):
        if cross_building(self):
            raise ConanInvalidConfiguration("Cross-building DXC requires native LLVM TableGen tools")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.17.2 <4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.variables["LLVM_TARGETS_TO_BUILD"] = "None"
        tc.variables["LLVM_DEFAULT_TARGET_TRIPLE"] = "dxil-ms-dx"
        tc.variables["LLVM_ENABLE_EH"] = True
        tc.variables["LLVM_ENABLE_RTTI"] = True
        tc.variables["LLVM_ENABLE_TERMINFO"] = False
        tc.variables["LLVM_ENABLE_ZLIB"] = False
        tc.variables["LLVM_INCLUDE_TESTS"] = False
        tc.variables["LLVM_INCLUDE_DOCS"] = False
        tc.variables["LLVM_INCLUDE_EXAMPLES"] = False
        tc.variables["LLVM_INCLUDE_UTILS"] = False
        tc.variables["LLVM_OPTIMIZED_TABLEGEN"] = False
        tc.variables["LIBCLANG_BUILD_STATIC"] = True
        tc.variables["CLANG_BUILD_EXAMPLES"] = False
        tc.variables["CLANG_ENABLE_ARCMT"] = False
        tc.variables["CLANG_ENABLE_STATIC_ANALYZER"] = False
        tc.variables["HLSL_INCLUDE_TESTS"] = False
        tc.variables["HLSL_BUILD_DXILCONV"] = False
        tc.variables["HLSL_ENABLE_FIXED_VER"] = True
        tc.variables["HLSL_SUPPORT_QUERY_GIT_COMMIT_INFO"] = False
        # Match the normal MSVC STL ABI used by the Conan SPIRV-Tools package.
        tc.variables["HLSL_ENABLE_DEBUG_ITERATORS"] = True
        tc.variables["ENABLE_SPIRV_CODEGEN"] = self.options.with_spirv
        tc.variables["SPIRV_BUILD_TESTS"] = False
        if self.settings.os != "Windows":
            tc.variables["DIRECTX_HEADER_INCLUDE_DIR"] = self.dependencies["directx-headers"].cpp_info.includedirs[0]
        if self.options.with_spirv:
            tc.variables["SPIRV_HEADER_INCLUDE_DIR"] = self.dependencies["spirv-headers"].cpp_info.includedirs[0]
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="dxc" if self.options.with_tools else "dxcompiler")

    def package(self):
        for filename in ("LICENSE.TXT", "ThirdPartyNotices.txt"):
            copy(self, filename, self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install(component="dxcompiler")
        cmake.install(component="dxc-headers")
        if self.options.with_tools:
            cmake.install(component="dxc")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "directx-shader-compiler")
        self.cpp_info.set_property("cmake_target_name", "directx-shader-compiler::dxcompiler")
        self.cpp_info.libs = ["dxcompiler"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
        if self.options.with_tools:
            self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        else:
            self.cpp_info.bindirs = ["bin"] if self.settings.os == "Windows" else []
