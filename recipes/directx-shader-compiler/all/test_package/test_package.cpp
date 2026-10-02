#ifdef _WIN32
#include <windows.h>
#endif
#include <dxc/dxcapi.h>

#include <cstdint>
#include <cstring>
#include <iostream>

bool compile(IDxcCompiler3 *compiler, bool spirv) {
    const char source[] = "float4 main() : SV_Target { return float4(1, 0, 0, 1); }";
    DxcBuffer buffer{source, sizeof(source) - 1, DXC_CP_UTF8};
    const wchar_t *args[] = {L"-E", L"main", L"-T", L"ps_6_0", L"-spirv"};
    IDxcResult *result = nullptr;
    HRESULT status = compiler->Compile(&buffer, args, spirv ? 5 : 4, nullptr,
                                       IID_PPV_ARGS(&result));
    if (FAILED(status)) {
        return false;
    }
    IDxcBlobUtf8 *errors = nullptr;
    result->GetOutput(DXC_OUT_ERRORS, IID_PPV_ARGS(&errors), nullptr);
    if (errors) {
        std::cerr << errors->GetStringPointer();
        errors->Release();
    }
    HRESULT compilation_status = E_FAIL;
    status = result->GetStatus(&compilation_status);
    IDxcBlob *object = nullptr;
    bool ok = SUCCEEDED(status) && SUCCEEDED(compilation_status) &&
              SUCCEEDED(result->GetResult(&object));
    if (ok) {
        std::uint32_t magic = 0;
        ok = object && object->GetBufferSize() >= sizeof(magic);
        if (ok) {
            std::memcpy(&magic, object->GetBufferPointer(), sizeof(magic));
            ok = spirv ? magic == 0x07230203 :
                         std::memcmp(object->GetBufferPointer(), "DXBC", 4) == 0;
        }
    }
    if (object) {
        object->Release();
    }
    result->Release();
    return ok;
}

int main() {
    IDxcCompiler3 *compiler = nullptr;
    if (FAILED(DxcCreateInstance(CLSID_DxcCompiler, IID_PPV_ARGS(&compiler)))) {
        return 1;
    }
    bool ok = compile(compiler, false);
#if TEST_SPIRV
    ok = compile(compiler, true) && ok;
#endif
    compiler->Release();
    return ok ? 0 : 1;
}
