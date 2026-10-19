import com.comsol.model.*;
import com.comsol.model.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.io.*;

/** COMSOL API adapter only: all PDE assembly, solution and evaluation use COMSOL. */
public class H0Thermal {
  static final String INPUT = "__INPUT_DIR__";
  static final String OUTPUT = "__RUN_DIR__";
  static final String LEVEL = "__LEVEL__";
  static final int NXY = __NXY__, NZ = __NZ__;

  static void planeSelection(Model m, String tag, int dim, String z) {
    m.component("comp1").selection().create(tag, "Box");
    m.component("comp1").selection(tag).set("entitydim", dim);
    m.component("comp1").selection(tag).set("condition", "inside");
    // Box selection uses rendered geometry; 10 nm padding avoids tessellation rounding.
    // This selection tolerance does not alter geometry or the 0.1 nm sampling tolerance.
    m.component("comp1").selection(tag).set("xmin", "-1e-8");
    m.component("comp1").selection(tag).set("xmax", "Lx+1e-8");
    m.component("comp1").selection(tag).set("ymin", "-1e-8");
    m.component("comp1").selection(tag).set("ymax", "Ly+1e-8");
    m.component("comp1").selection(tag).set("zmin", z+"-1e-8");
    m.component("comp1").selection(tag).set("zmax", z+"+1e-8");
  }

  public static Model run() throws Exception {
    ModelUtil.showProgress(true);
    Model m = ModelUtil.create("H0_"+LEVEL);
    m.label("H0 silicon thermal verification - "+LEVEL);
    m.modelPath(OUTPUT);
    // Inserted verbatim from the validated input by the Python orchestration layer.
    __PARAMETERS__
    m.component().create("comp1", true);
    m.component("comp1").geom().create("geom1", 3);
    m.component("comp1").geom("geom1").lengthUnit("m");
    m.component("comp1").geom("geom1").create("blk1", "Block");
    m.component("comp1").geom("geom1").feature("blk1").set("size", new String[]{"Lx","Ly","Lz"});
    m.component("comp1").geom("geom1").feature("blk1").set("pos", new String[]{"0","0","0"});
    m.component("comp1").geom("geom1").run();
    planeSelection(m,"top",2,"Lz");
    planeSelection(m,"bottom",2,"0");
    planeSelection(m,"bottomEdges",1,"0");
    int[] top = m.component("comp1").selection("top").entities(2);
    int[] bottom = m.component("comp1").selection("bottom").entities(2);
    int[] edges = m.component("comp1").selection("bottomEdges").entities(1);
    System.out.println("H0_SELECTION top="+Arrays.toString(top)+" bottom="+Arrays.toString(bottom)+" bottomEdges="+Arrays.toString(edges));
    System.out.println("H0_BOUNDS "+Arrays.toString(m.component("comp1").geom("geom1").getBoundingBox()));
    if (top.length!=1 || bottom.length!=1 || edges.length!=4) throw new IllegalStateException("Plane selection mismatch");

    m.component("comp1").material().create("mat1", "Common");
    m.component("comp1").material("mat1").label("Constant silicon - independent synthetic fixture");
    m.component("comp1").material("mat1").selection().all();
    m.component("comp1").material("mat1").propertyGroup("def").set("thermalconductivity", new String[]{"si_k","0","0","0","si_k","0","0","0","si_k"});
    m.component("comp1").material("mat1").propertyGroup("def").set("density", "si_rho");
    m.component("comp1").material("mat1").propertyGroup("def").set("heatcapacity", "si_cp");
    m.component("comp1").physics().create("ht", "HeatTransfer", "geom1");
    m.component("comp1").physics("ht").prop("ShapeProperty").set("order_temperature", 2);
    m.component("comp1").physics("ht").feature("init1").set("Tinit", "Tamb");
    m.component("comp1").physics("ht").create("hs1", "HeatSource", 3);
    m.component("comp1").physics("ht").feature("hs1").selection().all();
    m.component("comp1").physics("ht").feature("hs1").set("Q0", "qSi");
    m.component("comp1").physics("ht").create("hf1", "HeatFluxBoundary", 2);
    m.component("comp1").physics("ht").feature("hf1").selection().named("top");
    m.component("comp1").physics("ht").feature("hf1").set("HeatFluxType", "ConvectiveHeatFlux");
    m.component("comp1").physics("ht").feature("hf1").set("h", "hTop");
    m.component("comp1").physics("ht").feature("hf1").set("Text", "Tamb");

    m.component("comp1").mesh().create("mesh1");
    MeshSequence mesh = m.component("comp1").mesh("mesh1");
    mesh.create("map1", "Map");
    mesh.feature("map1").selection().named("bottom");
    mesh.feature("map1").create("dist1", "Distribution");
    mesh.feature("map1").feature("dist1").selection().named("bottomEdges");
    mesh.feature("map1").feature("dist1").set("numelem", NXY);
    mesh.feature("map1").feature("dist1").set("equidistant", true);
    mesh.create("swe1", "Sweep");
    mesh.feature("swe1").selection().geom(3).all();
    mesh.feature("swe1").selection("sourceface").geom(2).set(bottom);
    mesh.feature("swe1").selection("targetface").geom(2).set(top);
    mesh.feature("swe1").create("dist1", "Distribution");
    mesh.feature("swe1").feature("dist1").set("numelem", NZ);
    mesh.run();
    int hex = mesh.getNumElem("hex");
    if (hex != NXY*NXY*NZ) throw new IllegalStateException("Unexpected hexahedral element count: "+hex);

    m.study().create("std1");
    m.study("std1").create("stat", "Stationary");
    m.sol().create("sol1");
    m.sol("sol1").study("std1");
    m.sol("sol1").create("st1", "StudyStep");
    m.sol("sol1").feature("st1").set("study", "std1");
    m.sol("sol1").feature("st1").set("studystep", "stat");
    m.sol("sol1").create("v1", "Variables");
    m.sol("sol1").create("s1", "Stationary");
    m.sol("sol1").feature("s1").set("nonlin", "off");
    m.sol("sol1").feature("s1").feature("dDef").set("linsolver", "pardiso");
    m.sol("sol1").attach("std1");
    m.sol("sol1").runAll();
    if (m.sol("sol1").isEmpty()) throw new IllegalStateException("No solution stored");
    int dof = m.sol("sol1").getU().length;
    m.result().dataset().create("solData", "Solution");
    m.result().dataset("solData").set("solution", "sol1");

    double[][] xyz=__COORDINATES__;
    if (xyz[0].length!=16) throw new IllegalArgumentException("H0_z16 requires 16 points");
    m.result().numerical().create("sampleT", "Interp");
    m.result().numerical("sampleT").set("data", "solData");
    m.result().numerical("sampleT").set("expr", new String[]{"T"});
    m.result().numerical("sampleT").set("unit", "K");
    m.result().numerical("sampleT").set("ext", 0);
    m.result().numerical("sampleT").selection().all();
    m.result().numerical("sampleT").setInterpolationCoordinates(xyz);
    double[] temperatures=m.result().numerical("sampleT").getData()[0][0];
    if(temperatures.length!=16) throw new IllegalStateException("Incomplete temperature evaluation");
    // Emit raw COMSOL evaluations; Python only transcribes these records to CSV.
    for(int j=0;j<temperatures.length;j++) {
      if(!Double.isFinite(temperatures[j])) throw new IllegalStateException("Nonfinite temperature");
      System.out.printf(Locale.ROOT,"H0_TEMPERATURE %.17g,%.17g,%.17g,%.17g%n",xyz[0][j],xyz[1][j],xyz[2][j],temperatures[j]);
    }
    m.result().numerical().create("qin", "IntVolume");
    m.result().numerical("qin").set("data", "solData");
    m.result().numerical("qin").selection().all();
    m.result().numerical("qin").set("expr", new String[]{"qSi","1"});
    double[][] vi=m.result().numerical("qin").getReal();
    m.result().numerical().create("qout", "IntSurface");
    m.result().numerical("qout").set("data", "solData");
    m.result().numerical("qout").selection().named("top");
    m.result().numerical("qout").set("expr", new String[]{"hTop*(T-Tamb)","1","T","-si_k*(nx*Tx+ny*Ty+nz*Tz)"});
    double[][] si=m.result().numerical("qout").getReal();
    m.result().create("pg1", "PlotGroup3D");
    m.result("pg1").set("data", "solData");
    m.result("pg1").create("surf1", "Surface");
    m.result("pg1").feature("surf1").set("expr", "T");
    m.save(OUTPUT+"/h0_"+LEVEL+".mph");
    m.save(OUTPUT+"/h0_"+LEVEL+"_export.java", "java");
    Model saved = ModelUtil.load("Readback_"+LEVEL, OUTPUT+"/h0_"+LEVEL+".mph");
    if (saved.sol("sol1").isEmpty() || saved.sol("sol1").getU().length!=dof) throw new IllegalStateException("Saved solution missing");
    double[] restored=saved.result().numerical("sampleT").getData()[0][0];
    double readbackError=0;
    for(int j=0;j<16;j++) readbackError=Math.max(readbackError,Math.abs(restored[j]-temperatures[j]));
    if(readbackError>1e-12) throw new IllegalStateException("Saved solution differs from exported field");
    System.out.println("H0_READBACK max_abs_temperature_difference_k="+readbackError);
    System.out.println("H0_PHYSICS_FEATURES "+Arrays.toString(saved.component("comp1").physics("ht").feature().tags()));
    for(String tag : saved.component("comp1").physics("ht").feature().tags()) {
      System.out.println("H0_PHYSICS_TYPE "+tag+"="+saved.component("comp1").physics("ht").feature(tag).getType());
    }
    ModelUtil.remove("Readback_"+LEVEL);
    String json=String.format(Locale.ROOT,
      "{\"status\":\"solved\",\"solver_version\":\"%s\",\"level\":\"%s\",\"solution_vector_length\":%d,\"hexahedra\":%d,\"nxy\":%d,\"nz\":%d,\"temperature_order\":2,\"integrated_source_w\":%.17g,\"volume_m3\":%.17g,\"integrated_top_outward_heat_w\":%.17g,\"top_area_m2\":%.17g,\"top_average_temperature_k\":%.17g,\"top_conductive_outward_heat_w\":%.17g,\"top_boundaries\":%s,\"bottom_boundaries\":%s}%n",
      ModelUtil.getComsolVersion(), LEVEL,dof,hex,NXY,NZ,vi[0][0],vi[1][0],si[0][0],si[1][0],si[2][0]/si[1][0],si[3][0],Arrays.toString(top),Arrays.toString(bottom));
    System.out.println("H0_RESULT "+json);
    return m;
  }

  public static void main(String[] args) throws Exception {
    try { run(); } catch (Exception e) { e.printStackTrace(System.out); throw e; }
  }
}
