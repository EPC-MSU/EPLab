def edit_spec_file() -> None:
    spec_file_name = "main.spec"
    content = read_file(spec_file_name)

    i = content.find("pyz = PYZ(a.pure)")
    if i == -1:
        return

    # We exclude the libgdk_pixbuf library so that the build will work on different distributions with system libraries
    new_content = content[:i] + "a.binaries = [x for x in a.binaries if 'libgdk_pixbuf' not in x[0]]\n" + content[i:]

    write_file(spec_file_name, new_content)


def read_file(file_name: str) -> str:
    with open(file_name, "r", encoding="utf-8") as file:
        content = file.read()
    return content


def write_file(file_name: str, content: str) -> None:
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(content)


if __name__ == "__main__":
    edit_spec_file()
