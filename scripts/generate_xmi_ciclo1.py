import uuid

def g():
    return '{' + str(uuid.uuid4()).upper() + '}'

pkg_guid = g()
model_guid = g()

# Actores
act_vis = g()
act_dev = g()
act_sm = g()
act_adm = g()
act_tim = g()
act_gem = g()
act_speech = g()

# Casos de Uso
cu01 = g()
cu02 = g()
cu03 = g()
cu04 = g()
cu05 = g()
cu06 = g()
cu07 = g()

# Generalizaciones / Includes
gen_sm_dev = g()
gen_adm_sm = g()
inc_07_04 = g()

conns = [g() for _ in range(20)]

diag_main = g()
diag_cu1 = g()
diag_cu2 = g()
diag_cu3 = g()
diag_cu4 = g()
diag_cu5 = g()
diag_cu6 = g()
diag_cu7 = g()

xml_lines = [
    '<?xml version="1.0" encoding="windows-1252"?>',
    '<xmi:XMI xmi:version="2.1" xmlns:uml="http://schema.omg.org/spec/UML/2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1">',
    '	<xmi:Documentation exporter="Enterprise Architect" exporterVersion="6.5"/>',
    f'	<uml:Model xmi:type="uml:Model" name="EA_Model" xmi:id="EAID_{model_guid}">',
    f'		<packagedElement xmi:type="uml:Package" xmi:id="EAID_{pkg_guid}" name="Ciclo 1 - Nucleo y Modelado Base">',
    '',
    '			<!-- ACTORES HUMANOS -->',
    f'			<packagedElement xmi:type="uml:Actor" xmi:id="EAID_{act_vis}" name="Visitante"/>',
    f'			<packagedElement xmi:type="uml:Actor" xmi:id="EAID_{act_dev}" name="Desarrollador"/>',
    f'			<packagedElement xmi:type="uml:Actor" xmi:id="EAID_{act_sm}" name="Scrum Master">',
    f'				<generalization xmi:type="uml:Generalization" xmi:id="EAID_{gen_sm_dev}" general="EAID_{act_dev}"/>',
    '			</packagedElement>',
    f'			<packagedElement xmi:type="uml:Actor" xmi:id="EAID_{act_adm}" name="Administrador">',
    f'				<generalization xmi:type="uml:Generalization" xmi:id="EAID_{gen_adm_sm}" general="EAID_{act_sm}"/>',
    '			</packagedElement>',
    '',
    '			<!-- ACTORES EXTERNOS -->',
    f'			<packagedElement xmi:type="uml:Actor" xmi:id="EAID_{act_tim}" name="Temporizador del Sistema"/>',
    f'			<packagedElement xmi:type="uml:Actor" xmi:id="EAID_{act_speech}" name="Web Speech API"/>',
    f'			<packagedElement xmi:type="uml:Actor" xmi:id="EAID_{act_gem}" name="API Cloud Gemini (Vision / Multimodal)"/>',
    '',
    '			<!-- CASOS DE USO DEL CICLO 1 -->',
    f'			<packagedElement xmi:type="uml:UseCase" xmi:id="EAID_{cu01}" name="CU-01: Gestionar Autenticacion y Sesion de Usuario"/>',
    f'			<packagedElement xmi:type="uml:UseCase" xmi:id="EAID_{cu02}" name="CU-02: Administrar Equipos de Desarrollo y Miembros"/>',
    f'			<packagedElement xmi:type="uml:UseCase" xmi:id="EAID_{cu03}" name="CU-03: Gestionar Jerarquia de Proyectos y Diagramas"/>',
    f'			<packagedElement xmi:type="uml:UseCase" xmi:id="EAID_{cu04}" name="CU-04: Modelar Diagramas de Clases UML 2.5+ y Persistencia"/>',
    f'			<packagedElement xmi:type="uml:UseCase" xmi:id="EAID_{cu05}" name="CU-05: Colaborar en Tiempo Real en el Lienzo"/>',
    f'			<packagedElement xmi:type="uml:UseCase" xmi:id="EAID_{cu06}" name="CU-06: Interoperar Modelos y Generar Backend"/>',
    f'			<packagedElement xmi:type="uml:UseCase" xmi:id="EAID_{cu07}" name="CU-07: Generar y Modificar Diagramas con IA Multimodal">',
    f'				<include xmi:type="uml:Include" xmi:id="EAID_{inc_07_04}" addition="EAID_{cu04}"/>',
    '			</packagedElement>',
    '',
    '			<!-- ASOCIACIONES -->',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[0]}"><memberEnd xmi:idref="R1"/><memberEnd xmi:idref="R2"/><ownedEnd xmi:type="uml:Property" xmi:id="R1" type="EAID_{act_vis}"/><ownedEnd xmi:type="uml:Property" xmi:id="R2" type="EAID_{cu01}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[1]}"><memberEnd xmi:idref="R3"/><memberEnd xmi:idref="R4"/><ownedEnd xmi:type="uml:Property" xmi:id="R3" type="EAID_{act_dev}"/><ownedEnd xmi:type="uml:Property" xmi:id="R4" type="EAID_{cu01}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[2]}"><memberEnd xmi:idref="R5"/><memberEnd xmi:idref="R6"/><ownedEnd xmi:type="uml:Property" xmi:id="R5" type="EAID_{act_tim}"/><ownedEnd xmi:type="uml:Property" xmi:id="R6" type="EAID_{cu01}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[3]}"><memberEnd xmi:idref="R7"/><memberEnd xmi:idref="R8"/><ownedEnd xmi:type="uml:Property" xmi:id="R7" type="EAID_{act_sm}"/><ownedEnd xmi:type="uml:Property" xmi:id="R8" type="EAID_{cu02}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[4]}"><memberEnd xmi:idref="R9"/><memberEnd xmi:idref="R10"/><ownedEnd xmi:type="uml:Property" xmi:id="R9" type="EAID_{act_dev}"/><ownedEnd xmi:type="uml:Property" xmi:id="R10" type="EAID_{cu03}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[5]}"><memberEnd xmi:idref="R11"/><memberEnd xmi:idref="R12"/><ownedEnd xmi:type="uml:Property" xmi:id="R11" type="EAID_{act_dev}"/><ownedEnd xmi:type="uml:Property" xmi:id="R12" type="EAID_{cu04}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[6]}"><memberEnd xmi:idref="R13"/><memberEnd xmi:idref="R14"/><ownedEnd xmi:type="uml:Property" xmi:id="R13" type="EAID_{act_tim}"/><ownedEnd xmi:type="uml:Property" xmi:id="R14" type="EAID_{cu04}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[7]}"><memberEnd xmi:idref="R15"/><memberEnd xmi:idref="R16"/><ownedEnd xmi:type="uml:Property" xmi:id="R15" type="EAID_{act_dev}"/><ownedEnd xmi:type="uml:Property" xmi:id="R16" type="EAID_{cu05}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[8]}"><memberEnd xmi:idref="R17"/><memberEnd xmi:idref="R18"/><ownedEnd xmi:type="uml:Property" xmi:id="R17" type="EAID_{act_dev}"/><ownedEnd xmi:type="uml:Property" xmi:id="R18" type="EAID_{cu06}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[9]}"><memberEnd xmi:idref="R19"/><memberEnd xmi:idref="R20"/><ownedEnd xmi:type="uml:Property" xmi:id="R19" type="EAID_{act_dev}"/><ownedEnd xmi:type="uml:Property" xmi:id="R20" type="EAID_{cu07}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[10]}"><memberEnd xmi:idref="R21"/><memberEnd xmi:idref="R22"/><ownedEnd xmi:type="uml:Property" xmi:id="R21" type="EAID_{act_speech}"/><ownedEnd xmi:type="uml:Property" xmi:id="R22" type="EAID_{cu07}"/></packagedElement>',
    f'			<packagedElement xmi:type="uml:Association" xmi:id="EAID_{conns[11]}"><memberEnd xmi:idref="R23"/><memberEnd xmi:idref="R24"/><ownedEnd xmi:type="uml:Property" xmi:id="R23" type="EAID_{act_gem}"/><ownedEnd xmi:type="uml:Property" xmi:id="R24" type="EAID_{cu07}"/></packagedElement>',
    '		</packagedElement>',
    '	</uml:Model>',
    '',
    '	<xmi:Extension extender="Enterprise Architect" extenderID="6.5">',
    '		<elements>',
    f'			<element xmi:idref="EAID_{act_vis}" ea_type="Actor" name="Visitante" scope="public"/>',
    f'			<element xmi:idref="EAID_{act_dev}" ea_type="Actor" name="Desarrollador" scope="public"/>',
    f'			<element xmi:idref="EAID_{act_sm}" ea_type="Actor" name="Scrum Master" scope="public"/>',
    f'			<element xmi:idref="EAID_{act_adm}" ea_type="Actor" name="Administrador" scope="public"/>',
    f'			<element xmi:idref="EAID_{act_tim}" ea_type="Actor" name="Temporizador del Sistema" scope="public"><modifiers stereotype="temporizador"/></element>',
    f'			<element xmi:idref="EAID_{act_speech}" ea_type="Actor" name="Web Speech API" scope="public"><modifiers stereotype="browser api"/></element>',
    f'			<element xmi:idref="EAID_{act_gem}" ea_type="Actor" name="API Cloud Gemini (Vision / Multimodal)" scope="public"><modifiers stereotype="sistema externo"/></element>',
    f'			<element xmi:idref="EAID_{cu01}" ea_type="UseCase" name="CU-01: Gestionar Autenticacion y Sesion de Usuario" scope="public"/>',
    f'			<element xmi:idref="EAID_{cu02}" ea_type="UseCase" name="CU-02: Administrar Equipos de Desarrollo y Miembros" scope="public"/>',
    f'			<element xmi:idref="EAID_{cu03}" ea_type="UseCase" name="CU-03: Gestionar Jerarquia de Proyectos y Diagramas" scope="public"/>',
    f'			<element xmi:idref="EAID_{cu04}" ea_type="UseCase" name="CU-04: Modelar Diagramas de Clases UML 2.5+ y Persistencia" scope="public"/>',
    f'			<element xmi:idref="EAID_{cu05}" ea_type="UseCase" name="CU-05: Colaborar en Tiempo Real en el Lienzo" scope="public"/>',
    f'			<element xmi:idref="EAID_{cu06}" ea_type="UseCase" name="CU-06: Interoperar Modelos y Generar Backend" scope="public"/>',
    f'			<element xmi:idref="EAID_{cu07}" ea_type="UseCase" name="CU-07: Generar y Modificar Diagramas con IA Multimodal" scope="public"/>',
    '		</elements>',
    '		<connectors>',
    f'			<connector xmi:idref="EAID_{gen_sm_dev}"><source xmi:idref="EAID_{act_sm}"/><target xmi:idref="EAID_{act_dev}"/><properties ea_type="Generalization" direction="Source -> Destination"/></connector>',
    f'			<connector xmi:idref="EAID_{gen_adm_sm}"><source xmi:idref="EAID_{act_adm}"/><target xmi:idref="EAID_{act_sm}"/><properties ea_type="Generalization" direction="Source -> Destination"/></connector>',
    f'			<connector xmi:idref="EAID_{inc_07_04}"><source xmi:idref="EAID_{cu07}"/><target xmi:idref="EAID_{cu04}"/><properties ea_type="UseCase" stereotype="include" direction="Source -> Destination"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[0]}"><source xmi:idref="EAID_{act_vis}"/><target xmi:idref="EAID_{cu01}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[1]}"><source xmi:idref="EAID_{act_dev}"/><target xmi:idref="EAID_{cu01}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[2]}"><source xmi:idref="EAID_{act_tim}"/><target xmi:idref="EAID_{cu01}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[3]}"><source xmi:idref="EAID_{act_sm}"/><target xmi:idref="EAID_{cu02}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[4]}"><source xmi:idref="EAID_{act_dev}"/><target xmi:idref="EAID_{cu03}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[5]}"><source xmi:idref="EAID_{act_dev}"/><target xmi:idref="EAID_{cu04}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[6]}"><source xmi:idref="EAID_{act_tim}"/><target xmi:idref="EAID_{cu04}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[7]}"><source xmi:idref="EAID_{act_dev}"/><target xmi:idref="EAID_{cu05}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[8]}"><source xmi:idref="EAID_{act_dev}"/><target xmi:idref="EAID_{cu06}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[9]}"><source xmi:idref="EAID_{act_dev}"/><target xmi:idref="EAID_{cu07}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[10]}"><source xmi:idref="EAID_{act_speech}"/><target xmi:idref="EAID_{cu07}"/><properties ea_type="Association"/></connector>',
    f'			<connector xmi:idref="EAID_{conns[11]}"><source xmi:idref="EAID_{act_gem}"/><target xmi:idref="EAID_{cu07}"/><properties ea_type="Association"/></connector>',
    '		</connectors>',
    '		<diagrams>',
    '',
    '			<!-- DIAGRAMA COMPLETO DEL CICLO 1 -->',
    f'			<diagram xmi:id="EAID_{diag_main}">',
    f'				<model package="EAID_{pkg_guid}" name="Diagrama General - Ciclo 1" type="Use Case"/>',
    '				<properties documentation="Diagrama de Casos de Uso del Ciclo #1"/>',
    '				<project author="Alejandro Melgar" version="2.0"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=60;Right=150;Bottom=150;" subject="EAID_{act_vis}" seq="1"/>',
    f'					<element geometry="Left=60;Top=240;Right=150;Bottom=330;" subject="EAID_{act_dev}" seq="2"/>',
    f'					<element geometry="Left=60;Top=420;Right=150;Bottom=510;" subject="EAID_{act_sm}" seq="3"/>',
    f'					<element geometry="Left=60;Top=600;Right=150;Bottom=690;" subject="EAID_{act_adm}" seq="4"/>',
    f'					<element geometry="Left=880;Top=60;Right=1040;Bottom=130;" subject="EAID_{act_tim}" seq="5"/>',
    f'					<element geometry="Left=880;Top=360;Right=1040;Bottom=430;" subject="EAID_{act_speech}" seq="6"/>',
    f'					<element geometry="Left=880;Top=520;Right=1060;Bottom=590;" subject="EAID_{act_gem}" seq="7"/>',
    f'					<element geometry="Left=320;Top=60;Right=600;Bottom=120;" subject="EAID_{cu01}" seq="8"/>',
    f'					<element geometry="Left=320;Top=160;Right=600;Bottom=220;" subject="EAID_{cu02}" seq="9"/>',
    f'					<element geometry="Left=320;Top=260;Right=600;Bottom=320;" subject="EAID_{cu03}" seq="10"/>',
    f'					<element geometry="Left=320;Top=360;Right=600;Bottom=420;" subject="EAID_{cu04}" seq="11"/>',
    f'					<element geometry="Left=320;Top=460;Right=600;Bottom=520;" subject="EAID_{cu05}" seq="12"/>',
    f'					<element geometry="Left=320;Top=560;Right=600;Bottom=620;" subject="EAID_{cu06}" seq="13"/>',
    f'					<element geometry="Left=320;Top=660;Right=600;Bottom=720;" subject="EAID_{cu07}" seq="14"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '			<!-- DIAGRAMA INDIVIDUAL CU-01 -->',
    f'			<diagram xmi:id="EAID_{diag_cu1}">',
    f'				<model package="EAID_{pkg_guid}" name="CU-01: Autenticacion y Sesion" type="Use Case"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=60;Right=150;Bottom=150;" subject="EAID_{act_vis}"/>',
    f'					<element geometry="Left=60;Top=200;Right=150;Bottom=290;" subject="EAID_{act_dev}"/>',
    f'					<element geometry="Left=340;Top=120;Right=620;Bottom=180;" subject="EAID_{cu01}"/>',
    f'					<element geometry="Left=750;Top=120;Right=910;Bottom=190;" subject="EAID_{act_tim}"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '			<!-- DIAGRAMA INDIVIDUAL CU-02 -->',
    f'			<diagram xmi:id="EAID_{diag_cu2}">',
    f'				<model package="EAID_{pkg_guid}" name="CU-02: Equipos y Miembros" type="Use Case"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=60;Right=150;Bottom=150;" subject="EAID_{act_sm}"/>',
    f'					<element geometry="Left=60;Top=220;Right=150;Bottom=310;" subject="EAID_{act_adm}"/>',
    f'					<element geometry="Left=340;Top=120;Right=620;Bottom=180;" subject="EAID_{cu02}"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '			<!-- DIAGRAMA INDIVIDUAL CU-03 -->',
    f'			<diagram xmi:id="EAID_{diag_cu3}">',
    f'				<model package="EAID_{pkg_guid}" name="CU-03: Jerarquia de Proyectos" type="Use Case"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=100;Right=150;Bottom=190;" subject="EAID_{act_dev}"/>',
    f'					<element geometry="Left=340;Top=110;Right=620;Bottom=170;" subject="EAID_{cu03}"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '			<!-- DIAGRAMA INDIVIDUAL CU-04 -->',
    f'			<diagram xmi:id="EAID_{diag_cu4}">',
    f'				<model package="EAID_{pkg_guid}" name="CU-04: Modelado UML y Persistencia" type="Use Case"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=100;Right=150;Bottom=190;" subject="EAID_{act_dev}"/>',
    f'					<element geometry="Left=340;Top=110;Right=620;Bottom=170;" subject="EAID_{cu04}"/>',
    f'					<element geometry="Left=750;Top=110;Right=910;Bottom=180;" subject="EAID_{act_tim}"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '			<!-- DIAGRAMA INDIVIDUAL CU-05 -->',
    f'			<diagram xmi:id="EAID_{diag_cu5}">',
    f'				<model package="EAID_{pkg_guid}" name="CU-05: Colaboracion en Tiempo Real" type="Use Case"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=100;Right=150;Bottom=190;" subject="EAID_{act_dev}"/>',
    f'					<element geometry="Left=340;Top=110;Right=620;Bottom=170;" subject="EAID_{cu05}"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '			<!-- DIAGRAMA INDIVIDUAL CU-06 -->',
    f'			<diagram xmi:id="EAID_{diag_cu6}">',
    f'				<model package="EAID_{pkg_guid}" name="CU-06: Interoperabilidad y Backend" type="Use Case"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=100;Right=150;Bottom=190;" subject="EAID_{act_dev}"/>',
    f'					<element geometry="Left=340;Top=110;Right=620;Bottom=170;" subject="EAID_{cu06}"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '			<!-- DIAGRAMA INDIVIDUAL CU-07 -->',
    f'			<diagram xmi:id="EAID_{diag_cu7}">',
    f'				<model package="EAID_{pkg_guid}" name="CU-07: IA Multimodal y Modelado" type="Use Case"/>',
    '				<elements>',
    f'					<element geometry="Left=60;Top=120;Right=150;Bottom=210;" subject="EAID_{act_dev}"/>',
    f'					<element geometry="Left=340;Top=130;Right=620;Bottom=190;" subject="EAID_{cu07}"/>',
    f'					<element geometry="Left=340;Top=300;Right=620;Bottom=360;" subject="EAID_{cu04}"/>',
    f'					<element geometry="Left=750;Top=80;Right=910;Bottom=150;" subject="EAID_{act_speech}"/>',
    f'					<element geometry="Left=750;Top=200;Right=930;Bottom=270;" subject="EAID_{act_gem}"/>',
    '				</elements>',
    '			</diagram>',
    '',
    '		</diagrams>',
    '	</xmi:Extension>',
    '</xmi:XMI>'
]

content = '\n'.join(xml_lines)

p1 = r'c:\Users\Ale\Documents\SW1 2-2026\segundo examen parcial\diagrama_ciclo1_v2.xmi'
p2 = r'c:\Users\Ale\Documents\SW1 2-2026\documentos\diagrama_ciclo1_v2.xmi'

with open(p1, 'w', encoding='utf-8') as f:
    f.write(content)

with open(p2, 'w', encoding='utf-8') as f:
    f.write(content)

print('XMI files for Ciclo 1 written successfully.')
