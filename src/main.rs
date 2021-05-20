use glium::{glutin, Surface};
use liquidfun::box2d::{collision::shapes::polygon_shape::from_shape, common::math::Vec2};

#[macro_use]
extern crate glium;

mod model;

const VERTEX_SHADER_SRC: &str = r#"
        #version 140
        in vec2 position;
        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
        }
    "#;

const FRAGMENT_SHADER_SRC: &str = r#"
        #version 140
        uniform vec3 fill;
        out vec4 color;
        void main() {
            color = vec4(fill, 1.0);
        }
    "#;

const OCTOPUS_COLOR: [f32; 3] = [1.0, 0.93, 0.48];
const WALL_COLOR: [f32; 3] = [0.16, 0.62, 0.56];
const BACKGROUND_COLOR: [f32; 3] = [0.07, 0.13, 0.16];

#[derive(Copy, Clone)]
struct Vertex {
    position: [f32; 2],
}
implement_vertex!(Vertex, position);

impl std::convert::From<Vec2> for Vertex {
    fn from(vec: Vec2) -> Self {
        Vertex {
            position: [vec.x/SCALEX, vec.y/SCALEY],
        }
    }
}

const SCALEX: f32 = 22.0;
const SCALEY: f32 = 16.0;

fn transform(v: &Vec2, angle: f32, translate: &Vec2) -> Vec2 {
    Vec2 {
        x: v.x * angle.cos() - v.y * angle.sin() + translate.x,
        y: v.x * angle.sin() + v.y * angle.cos() + translate.y,
    }
}

fn main() {
    let event_loop = glutin::event_loop::EventLoop::new();
    let wb = glutin::window::WindowBuilder::new()
        .with_title("Octopus lab 🐙");
    let cb = glutin::ContextBuilder::new();
    let display = glium::Display::new(wb, cb, &event_loop).unwrap();

    let mut model = model::Model::default();
    // let buffer = model.particle_system.get_position_buffer();

    let program = glium::Program::from_source(&display, VERTEX_SHADER_SRC, FRAGMENT_SHADER_SRC, None).unwrap();
    let mut rects = Vec::new();

    for body in model.world.get_body_iterator() {
        let shape = from_shape(body.get_fixture_list().unwrap().get_shape());

        let pos = body.get_position();

        // A rectangle can be represented by two triangles. Append 2 triangles.
        let v1 = Vertex::from(transform(shape.get_vertex(0), body.get_angle(), pos));
        let v2 = Vertex::from(transform(shape.get_vertex(1), body.get_angle(), pos));
        let v3 = Vertex::from(transform(shape.get_vertex(2), body.get_angle(), pos));
        let v4 = Vertex::from(transform(shape.get_vertex(3), body.get_angle(), pos));
        rects.push(v1); rects.push(v2); rects.push(v3);
        rects.push(v1); rects.push(v4); rects.push(v3);
    }
    let static_buffer = glium::VertexBuffer::new(&display, &rects).unwrap();
    let stindices = glium::index::NoIndices(glium::index::PrimitiveType::TrianglesList);

    let mut t = 0;
    event_loop.run(move |ev, _, control_flow| {
        model.update(t);
        t += 1;

        let mut vertices = Vec::with_capacity(model.particle_system.get_particle_count() as usize);
        for p in model.particle_system.get_position_buffer() {
            vertices.push(Vertex { position: [p.x/SCALEX, p.y/SCALEY] });
        }

        let vertex_buffer = glium::VertexBuffer::dynamic(&display, &vertices).unwrap();
        let indices = glium::index::NoIndices(glium::index::PrimitiveType::Points);

        let mut target = display.draw();
        target.clear_color(BACKGROUND_COLOR[0], BACKGROUND_COLOR[1], BACKGROUND_COLOR[2], 1.0);
        let params = glium::DrawParameters {
            point_size: Some(4.0),
            .. Default::default()
        };

        target.draw(&vertex_buffer, &indices, &program, &uniform! { fill: OCTOPUS_COLOR },
                    &params).unwrap();

        if model.drawwalls {
            target.draw(&static_buffer, &stindices, &program, &uniform! { fill: WALL_COLOR },
                        &Default::default()).unwrap();
        }

        target.finish().unwrap();

        *control_flow = glutin::event_loop::ControlFlow::Poll;
        if model.finished {
            *control_flow = glutin::event_loop::ControlFlow::Exit;
        }

        match ev {
            glutin::event::Event::WindowEvent { event, .. } => match event {
                glutin::event::WindowEvent::CloseRequested => {
                    *control_flow = glutin::event_loop::ControlFlow::Exit;
                    return;
                },
                _ => return,
            },
            _ => (),
        }
    });
}
