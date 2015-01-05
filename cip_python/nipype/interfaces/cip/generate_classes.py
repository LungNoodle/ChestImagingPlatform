"""This script generates CIP Interfaces based on the CLI modules XML. CLI
modules are selected from the hardcoded list below and generated code is placed
in the cli_modules.py file (and imported in __init__.py). For this to work
correctly you must have your CLI executabes in $PATH"""

import xml.dom.minidom
import subprocess
import os
from shutil import rmtree

import keyword
python_keywords = keyword.kwlist  # If c++ SEM module uses one of these key words as a command line parameter, we need to modify variable


def force_to_valid_python_variable_name(old_name):
    """  Valid c++ names are not always valid in python, so
    provide alternate naming

    >>> force_to_valid_python_variable_name('lambda')
    'opt_lambda'
    >>> force_to_valid_python_variable_name('inputVolume')
    'inputVolume'
    """
    new_name = old_name
    new_name = new_name.lstrip().rstrip()
    if old_name in python_keywords:
        new_name = 'opt_' + old_name
    return new_name


def add_class_to_package(class_codes, class_names, module_name, package_dir):
    module_python_filename = os.path.join(package_dir, "%s.py" % module_name)
    f_m = open(module_python_filename, 'w')
    f_i = open(os.path.join(package_dir, "__init__.py"), 'a+')
    f_m.write("""# -*- coding: utf8 -*-
\"\"\"Autogenerated file - DO NOT EDIT
If you spot a bug, please report it on the mailing list and/or change the generator.\"\"\"\n\n""")
    imports = """from nipype.interfaces.base import CommandLine, CommandLineInputSpec, SEMLikeCommandLine, TraitedSpec, File, Directory, traits, isdefined, InputMultiPath, OutputMultiPath
import os\n\n\n"""
    f_m.write(imports)
    f_m.write("\n\n".join(class_codes).encode('utf8'))
    f_i.write("from %s import %s\n" % (module_name, ", ".join(class_names)))
    f_m.close()
    f_i.close()


def crawl_code_struct(code_struct, package_dir):
    subpackages = []
    for k, v in code_struct.iteritems():
        if isinstance(v, str) or isinstance(v, unicode):
            module_name = k.lower()
            class_name = k
            class_code = v
            add_class_to_package(
                [class_code], [class_name], module_name, package_dir)
        else:
            l1 = {}
            l2 = {}
            for key in v.keys():
                if (isinstance(v[key], str) or isinstance(v[key], unicode)):
                    l1[key] = v[key]
                else:
                    l2[key] = v[key]
            if l2:
                v = l2
                subpackages.append(k.lower())
                f_i = open(os.path.join(package_dir, "__init__.py"), 'a+')
                f_i.write("from %s import *\n" % k.lower())
                f_i.close()
                new_pkg_dir = os.path.join(package_dir, k.lower())
                if os.path.exists(new_pkg_dir):
                    rmtree(new_pkg_dir)
                os.mkdir(new_pkg_dir)
                crawl_code_struct(v, new_pkg_dir)
                if l1:
                    for ik, iv in l1.iteritems():
                        crawl_code_struct({ik: {ik: iv}}, new_pkg_dir)
            elif l1:
                v = l1
                module_name = k.lower()
                add_class_to_package(
                    v.values(), v.keys(), module_name, package_dir)
        if subpackages:
            f = open(os.path.join(package_dir, "setup.py"), 'w')
            f.write("""# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration

    config = Configuration('{pkg_name}', parent_package, top_path)

    {sub_pks}

    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(**configuration(top_path='').todict())
""".format(pkg_name=package_dir.split("/")[-1], sub_pks="\n    ".join(["config.add_data_dir('%s')" % sub_pkg for sub_pkg in subpackages])))
            f.close()


def generate_all_classes(modules_list=[], launcher=[],module_name=None):
    """ modules_list contains all the SEM compliant tools that should have wrappers created for them.
        launcher containtains the command line prefix wrapper arugments needed to prepare
        a proper environment for each of the modules.
    """
    all_code = {}
    for module in modules_list:
        print("=" * 80)
        print("Generating Definition for module {0}".format(module))
        print("^" * 80)
        package, code = generate_class(module, launcher)
        cur_package = all_code
        if module_name==None:
          module_name = package.strip().split(" ")[0].split(".")[-1]
        for package in package.strip().split(" ")[0].split(".")[:-1]:
            if package not in cur_package:
                cur_package[package] = {}
            cur_package = cur_package[package]
        if module_name not in cur_package:
            cur_package[module_name] = {}
        cur_package[module_name][module] = code
    if os.path.exists("__init__.py"):
        os.unlink("__init__.py")
    crawl_code_struct(all_code, os.getcwd())


def generate_class(module, launcher):
    dom = grab_xml(module, launcher)
    inputTraits = []
    outputTraits = []
    outputs_filenames = {}

    #self._outputs_nodes = []

    class_string = "\"\"\""

    for desc_str in ['title', 'category', 'description', 'version',
                     'documentation-url', 'license', 'contributor',
                     'acknowledgements']:
        el = dom.getElementsByTagName(desc_str)
        if el and el[0].firstChild:
            class_string += desc_str + ": " + el[
                0].firstChild.nodeValue + "\n\n"
        if desc_str == 'category':
            category = el[0].firstChild.nodeValue
    class_string += "\"\"\""

    for paramGroup in dom.getElementsByTagName("parameters"):
        indices = paramGroup.getElementsByTagName('index')
        max_index = 0
        for index in indices:
            if int(index.firstChild.nodeValue) > max_index:
                max_index = int(index.firstChild.nodeValue)
        for param in paramGroup.childNodes:
            if param.nodeName in ['label', 'description', '#text', '#comment']:
                continue
            traitsParams = {}

            longFlagNode = param.getElementsByTagName('longflag')
            if longFlagNode:
                ## Prefer to use longFlag as name if it is given, rather than the parameter name
                longFlagName = longFlagNode[0].firstChild.nodeValue
                ## SEM automatically strips prefixed "--" or "-" from from xml before processing
                ##     we need to replicate that behavior here The following
                ##     two nodes in xml have the same behavior in the program
                ##     <longflag>--test</longflag>
                ##     <longflag>test</longflag>
                longFlagName = longFlagName.lstrip(" -").rstrip(" ")
                name = longFlagName
                name = force_to_valid_python_variable_name(name)
                traitsParams["argstr"] = "--" + longFlagName + " "
            else:
                name = param.getElementsByTagName(
                    'name')[0].firstChild.nodeValue
                name = force_to_valid_python_variable_name(name)
                if param.getElementsByTagName('index'):
                    traitsParams["argstr"] = ""
                else:
                    traitsParams["argstr"] = "--" + name + " "

            if param.getElementsByTagName('description') and param.getElementsByTagName('description')[0].firstChild:
                traitsParams["desc"] = param.getElementsByTagName('description')[0].firstChild.nodeValue.replace('"', "\\\"").replace("\n", ", ")

            argsDict = {'directory': '%s', 'file': '%s', 'integer': "%d",
                        'double': "%f", 'float': "%f", 'image': "%s",
                        'transform': "%s", 'boolean': '',
                        'string-enumeration': '%s', 'string': "%s",
                        'integer-enumeration': '%s',
                        'table': '%s', 'point': '%s', 'region': '%s', 'geometry': '%s'}

            if param.nodeName.endswith('-vector'):
                traitsParams["argstr"] += "%s"
            else:
                traitsParams["argstr"] += argsDict[param.nodeName]

            index = param.getElementsByTagName('index')
            if index:
                traitsParams["position"] = int(
                    index[0].firstChild.nodeValue) - (max_index + 1)

            desc = param.getElementsByTagName('description')
            if index:
                traitsParams["desc"] = desc[0].firstChild.nodeValue

            typesDict = {'integer': "traits.Int", 'double': "traits.Float",
                         'float': "traits.Float", 'image': "File",
                         'transform': "File", 'boolean': "traits.Bool",
                         'string': "traits.Str", 'file': "File", 'geometry': "File",
                         'directory': "Directory", 'table': "File",
                         'point': "traits.List", 'region': "traits.List"}

            if param.nodeName.endswith('-enumeration'):
                type = "traits.Enum"
                values = ['"%s"' % el.firstChild.nodeValue for el in param.getElementsByTagName('element')]
            elif param.nodeName.endswith('-vector'):
                type = "InputMultiPath"
                if param.nodeName in ['file', 'directory', 'image', 'geometry', 'transform', 'table']:
                    values = ["%s(exists=True)" % typesDict[
                              param.nodeName.replace('-vector', '')]]
                else:
                    values = [typesDict[param.nodeName.replace('-vector', '')]]
                traitsParams["sep"] = ','
            elif param.getAttribute('multiple') == "true":
                type = "InputMultiPath"
                if param.nodeName in ['file', 'directory', 'image', 'geometry', 'transform', 'table']:
                    values = ["%s(exists=True)" % typesDict[param.nodeName]]
                elif param.nodeName in ['point', 'region']:
                    values = ["%s(traits.Float(), minlen=3, maxlen=3)" %
                              typesDict[param.nodeName]]
                else:
                    values = [typesDict[param.nodeName]]
                traitsParams["argstr"] += "..."
            else:
                values = []
                type = typesDict[param.nodeName]

            if param.nodeName in ['file', 'directory', 'image', 'geometry', 'transform', 'table']:
                if not param.getElementsByTagName('channel'):
                    raise RuntimeError("Insufficient XML specification: each element of type 'file', 'directory', 'image', 'geometry', 'transform',  or 'table' requires 'channel' field.\n{0}".format(traitsParams))
                elif param.getElementsByTagName('channel')[0].firstChild.nodeValue == 'output':
                    traitsParams["hash_files"] = False
                    inputTraits.append(
                        "%s = traits.Either(traits.Bool, %s(%s), %s)" % (name,
                                                                         type,
                                                                         parse_values(
                                                                         values).replace("exists=True", ""),
                                                                         parse_params(traitsParams)))
                    traitsParams["exists"] = True
                    traitsParams.pop("argstr")
                    traitsParams.pop("hash_files")
                    outputTraits.append("%s = %s(%s%s)" % (name, type.replace("Input", "Output"), parse_values(values), parse_params(traitsParams)))

                    outputs_filenames[
                        name] = gen_filename_from_param(param, name)
                elif param.getElementsByTagName('channel')[0].firstChild.nodeValue == 'input':
                    if param.nodeName in ['file', 'directory', 'image', 'geometry', 'transform', 'table'] and type not in ["InputMultiPath", "traits.List"]:
                        traitsParams["exists"] = True
                    inputTraits.append("%s = %s(%s%s)" % (name, type, parse_values(values), parse_params(traitsParams)))
                else:
                    raise RuntimeError("Insufficient XML specification: each element of type 'file', 'directory', 'image', 'geometry', 'transform',  or 'table' requires 'channel' field to be in ['input','output'].\n{0}".format(traitsParams))
            else:  # For all other parameter types, they are implicitly only input types
                inputTraits.append("%s = %s(%s%s)" % (name, type, parse_values(
                    values), parse_params(traitsParams)))

    input_spec_code = "class " + module + "InputSpec(CommandLineInputSpec):\n"
    for trait in inputTraits:
        input_spec_code += "    " + trait + "\n"

    output_spec_code = "class " + module + "OutputSpec(TraitedSpec):\n"
    if not outputTraits:
        output_spec_code += "    pass\n"
    else:
        for trait in outputTraits:
            output_spec_code += "    " + trait + "\n"

    output_filenames_code = "_outputs_filenames = {"
    output_filenames_code += ",".join(["'%s':'%s'" % (
        key, value) for key, value in outputs_filenames.iteritems()])
    output_filenames_code += "}"

    input_spec_code += "\n\n"
    output_spec_code += "\n\n"

    template = """class %name%(SEMLikeCommandLine):
    %class_str%

    input_spec = %name%InputSpec
    output_spec = %name%OutputSpec
    _cmd = "%launcher% %name% "
    %output_filenames_code%\n"""

    main_class = template.replace('%class_str%', class_string).replace("%name%", module).replace("%output_filenames_code%", output_filenames_code).replace("%launcher%", " ".join(launcher))

    return category, input_spec_code + output_spec_code + main_class


def grab_xml(module, launcher):
#        cmd = CommandLine(command = "Slicer3", args="--launch %s --xml"%module)
#        ret = cmd.run()
    command_list = launcher[:]  # force copy to preserve original
    command_list.extend([module, "--xml"])
    final_command = " ".join(command_list)
    xmlReturnValue = subprocess.Popen(
        final_command, stdout=subprocess.PIPE, shell=True).communicate()[0]
    return xml.dom.minidom.parseString(xmlReturnValue)
#        if ret.runtime.returncode == 0:
#            return xml.dom.minidom.parseString(ret.runtime.stdout)
#        else:
#            raise Exception(cmd.cmdline + " failed:\n%s"%ret.runtime.stderr)


def parse_params(params):
    list = []
    for key, value in params.iteritems():
        if isinstance(value, str) or isinstance(value, unicode):
            list.append('%s="%s"' % (key, value.replace('"', "'")))
        else:
            list.append('%s=%s' % (key, value))

    return ", ".join(list)


def parse_values(values):
    values = ['%s' % value for value in values]
    if len(values) > 0:
        retstr = ", ".join(values) + ", "
    else:
        retstr = ""
    return retstr


def gen_filename_from_param(param, base):
    fileExtensions = param.getAttribute("fileExtensions")
    if fileExtensions:
        ## It is possible that multiple file extensions can be specified in a
        ## comma separated list,  This will extract just the first extension
        firstFileExtension = fileExtensions.split(',')[0]
        ext = firstFileExtension
    else:
        ext = {'image': '.nii', 'transform': '.mat', 'file': '',
               'directory': '', 'geometry': '.vtk'}[param.nodeName]
    return base + ext

if __name__ == "__main__":
    ## NOTE:  For now either the launcher needs to be found on the default path, or
    ##        every tool in the modules list must be found on the default path
    ##        AND calling the module with --xml must be supported and compliant.
  
    
    #Get list of modules from directory name in CommandLineTools
    dir='../../../../CommandLineTools/'
    modules_list = [str.split(x[0],'/')[5] for x in os.walk(dir)]
    #Remove duplicates and sort list
    modules_list = list(set(modules_list))
    modules_list.sort()
    #Remove empty entries
    modules_list.remove('')
  
    print 'Number of modules founds ' + str(len(modules_list))


    ## SlicerExecutionModel compliant tools that are usually statically built, and don't need the Slicer3 --launcher
    generate_all_classes(modules_list=modules_list,launcher=[],module_name='cip')
    ## Tools compliant with SlicerExecutionModel called from the Slicer environment (for shared lib compatibility)
    #launcher = ['/home/raid3/gorgolewski/software/slicer/Slicer', '--launch']
    #generate_all_classes(modules_list=modules_list, launcher=launcher)
    #generate_all_classes(modules_list=['BRAINSABC'], launcher=[] )